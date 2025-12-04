import os
from multiprocessing import Lock, cpu_count
from pathlib import Path
from queue import Queue
from threading import Event, Thread
from typing import Optional, TypeVar, Callable, Protocol
from ctypes import c_int
from datetime import datetime
import termios
import sys
import traceback

import pandas as pd
from rich.console import Console, ConsoleOptions, ConsoleRenderable
from rich.control import Control
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TimeElapsedColumn,
)
from pydantic import Field

from wizard.base import Serializable
from wizard.sheet import Book, Sheet
from wizard.cell import Cell
from wizard.classifier import EquivalentClassChecker, Result
from wizard.utils import (
    suppress_output,
    get_logger,
    alt_screen_setup,
    alt_screen_teardown,
    PoolHolder,
)
from wizard.utils.google.client import BackOffClient
from wizard.software import Software, Excel, Gsheet, Calc
from wizard.argumentation import Dataset


class Task(Protocol):
    """A protocol has a uid field."""

    uid: Path | str


SheetName = TypeVar("SheetName")


class FeedBack(Protocol):
    name: SheetName
    uid: Path | str
    result: Result


@suppress_output
def validate(
    software: Software,
    task_queue: Queue[Optional[Task]],
    feedback_queue: Queue[Optional[FeedBack]],
    task2feedback: Callable[[Task, SheetName, Result], FeedBack],
    progress_queue: Queue[Optional[Path]],
    indistinguishable_counter: c_int,
    indistinguishable_counter_lock: Lock,
    store_host: str = "localhost",
    store_port: int = 6379,
):
    """Validates the spreadsheets and reports feedback and progress.

    Args:
        task_queue (Queue): A queue used for retrieving book paths.
        feedback_queue (Queue): A queue used for storing validation feedback for consumers.
        progress_queue (Queue): A queue used for reporting progress.
        task2feedback (Callable): A function that converts a task, sheet name, and sheet classification result into feedback.
        indistinguishable_counter (c_int): A counter for tracking the number of indistinguishable sheets.
        indistinguishable_counter_lock (Lock): A lock used for synchronizing access to the indistinguishable_counter.
    """
    logger = get_logger(file=__name__ + ".log", console=False)
    store = Dataset(software.name, host=store_host, port=store_port)

    while True:
        task = task_queue.get()
        task_queue.task_done()

        # The sentinel value 'None' is used to notify that the worker will stop.
        if task is None:
            logger.info(f"Process {os.getpid()} received None, stopping")
            feedback_queue.put(None)
            progress_queue.put(None)
            break

        logger.info(f"Process {os.getpid()}, Processing task {task}")
        # report progress when a task is received
        progress_queue.put(task.uid)
        try:
            # setup to validate the spreadsheet
            book = software.load(task.uid)
            store.set_book(book)

            for name, sheet in book.sheets.items():
                classifier = EquivalentClassChecker(software, sheet)
                result = classifier.validate()
                feedback = task2feedback(task, name, result)
                feedback_queue.put(feedback)

                if not result.distinguishable:
                    # update indistinguishable_counter
                    with indistinguishable_counter_lock:
                        indistinguishable_counter.value += 1
                    break
        except Exception as e:
            logger.exception(
                f"Process {os.getpid()}, uid: {task.uid}, Error: {e}, {traceback.format_exc()}"
            )


class LivePro(Live):
    """Add capability to move cursor to some position when finished refresh"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.relx = 0
        self.rely = 0

    def move(self, x: int, y: int) -> None:
        """Move cursor to relative position."""
        self.relx = x
        self.rely = y
        self.refresh()

    def reset(self) -> None:
        """Reset cursor position."""
        self.relx = 0
        self.rely = 0
        self.refresh()

    def process_renderables(
        self, renderables: list[ConsoleRenderable]
    ) -> list[ConsoleRenderable]:
        """Process renderables and move cursor to relative position."""
        renderables = super().process_renderables(renderables)
        renderables.append(Control.move(self.relx, self.rely))

        return renderables


class ConsoleRenderable(Console):
    """A renderable console that can be used in a rich layout."""

    def __init__(self, file=open(os.devnull, "w"), *args, **kwargs):
        super().__init__(record=True, file=file, *args, **kwargs)
        self.live: Optional[LivePro] = None

        self.row = 0
        self.col = 0

    def set_live(self, live: LivePro) -> None:
        with self._lock:
            self.live = live

    def clear(self, home: bool = True) -> None:
        with self._record_buffer_lock:
            self._record_buffer.clear()
        self.live.refresh()

    def __rich_console__(self, console: Console, options: ConsoleOptions):
        """Protocol method to render console."""

        self.col, self.row = 0, 0
        idx, newlines = len(self._record_buffer), 0
        # find the last n newlines
        for segment in self._record_buffer[::-1]:
            idx -= 1
            if "\n" in segment.text:
                newlines += 1
            if newlines < 1:
                self.col += len(segment.text)
            if newlines == options.height:
                break

        self.row = newlines

        with self._record_buffer_lock:
            for segment in self._record_buffer[idx:]:
                # highlight text if needed
                if not segment.style and self._highlight:
                    yield from self.highlighter(segment.text).render(console)
                else:
                    yield segment

    def input(self, prompt: str, padding: tuple = None) -> str:
        # cursor is totally wrong when using input

        with self._record_buffer_lock:
            for segment in self.render_str(prompt).render(self.live.console):
                self._record_buffer.append(segment)

        self.live.console.show_cursor()
        # refresh live console to show the prompt and update self.row and self.col
        self.live.refresh()
        if padding:
            self.live.move(
                self.col + padding[0] - self.width, self.row - self.height + padding[1]
            )

        text = input()
        self.live.reset()

        return text


class CacheSlot(Serializable):
    path: str
    last_modified: datetime


class Cache(Serializable):
    """A cache to store the last modified time of the files."""

    slots: list[CacheSlot] = Field(default_factory=list)

    def add(self, path: Path):
        slot = CacheSlot(
            path=str(path.resolve()),
            last_modified=datetime.fromtimestamp(path.stat().st_mtime),
        )
        self.slots.append(slot)

    def update(self, path: Path):
        """Update path in the cache if it exists. Otherwise, add it."""
        exist = False
        path = path.resolve()
        for slot in self.slots:
            if slot.path == str(path):
                exist = True
                slot.last_modified = datetime.fromtimestamp(path.stat().st_mtime)

        if not exist:
            self.add(path)

    def remove(self, path: Path):
        path = path.resolve()
        self.slots = [slot for slot in self.slots if slot.path != str(path)]

    def contains(self, path: Path) -> bool:
        """Check if the path is in the cache and has the same last modified time."""
        path = path.resolve()
        return any(
            slot.path == str(path)
            and slot.last_modified == datetime.fromtimestamp(path.stat().st_mtime)
            for slot in self.slots
        )


class ValidationTask(Serializable):
    """A minimal task type for validation."""

    uid: Path | str


class ValidationFeedBack(Serializable):
    """A minimal feedback type for validation."""

    name: str | int
    uid: Path | str
    result: Result


def validation_task2feedback(
    task: ValidationTask, name: SheetName, result: Result
) -> ValidationFeedBack:
    return ValidationFeedBack(name=name, uid=task.uid, result=result)


class BatchValidator:
    """A batch validator that validates spreadsheets in parallel and provides a user-friendly terminal interface.

    Example:
        1. Parallel validate all spreadsheets in the directory.
        >>> from pathlib import Path
        >>> from wizard.batch_validator import BatchValidator
        ...
        >>> validator = BatchValidator()
        >>> validator.validate(Path("datasets"))

        2. Add tasks manually and run the validator.
        >>> from pathlib import Path
        >>> from wizard.batch_validator import BatchValidator
        >>> from wizard.base import Serializable
        >>> from wizard.classifier import Result
        ...
        >>> # define task and feedback
        >>> class Task(Serializable):
        ...     uid: Path
        ...
        >>> class FeedBack(Serializable):
        ...     uid: Path
        ...     result: Result
        ...     name: str | int
        ...
        >>> def task2feedback(task: Task, name: str | int, result: Result) -> FeedBack:
        ...     return FeedBack(uid=task.uid, name=name, result=result)
        ...
        >>> # create a validator
        >>> validator = BatchValidator()
        >>> # add tasks to the validator
        >>> for task in [
        ...     Task(uid=Path("path/to/spreadsheet1")),
        ...     Task(uid=Path("path/to/spreadsheet2")),
        ... ]:
        ...     validator.submit(task)
        >>> # run the validator
        >>> feedbacks = validator.run(task2feedback)
    """

    def __init__(
        self,
        software: Software,
        host: str = "localhost",
        port: int = 6379,
        num_workers: int = cpu_count(),
    ) -> None:
        # Configure logging for the main process
        self.logger = get_logger(__name__)

        self.num_workers = num_workers
        self.pool = PoolHolder(num_workers=num_workers)

        # queue where main process get feedbacks
        self.feedback_queue: Queue[Optional[FeedBack]] = self.pool.queue()
        # queue where worker processes get tasks
        self.validation_task_queue: Queue[Optional[Task]] = self.pool.queue()
        # shared between worker processes and main process to report worker progress
        self.validation_progress_queue: Queue[Optional[Path]] = self.pool.queue()

        self.software = software
        self.store_host = host
        self.store_port = port

        # a renderable console that can be used in a rich layout
        self.console = ConsoleRenderable()

        # Precisely track the number of indistinguishable sheets because feedback_queue.size() is not accurate
        self.counter = self.pool.value(c_int, 0)
        self.counter_lock = self.pool.lock()

    def _render_validation_progress(self, progress: Progress, task_id: int):
        """Renders the validation progress in the console."""

        finished = 0
        while finished < self.num_workers:
            path = self.validation_progress_queue.get()
            if path is None:
                finished += 1
                continue

            progress.update(
                task_id, advance=1, description=f"[cyan]Validate [i b]{path}[/]"
            )

        progress.update(task_id, description="[cyan]Done!")

    def _render_classfication_progress(self, layout: Layout, done: Event):
        """Renders the classification progress in the console."""

        while not done.wait(0.5):
            with self.counter_lock:
                size = self.counter.value

            if not done.is_set():
                if size == 0:
                    layout.update(
                        Panel(
                            "[b i]Good luck! No tasks will dirty your hands for now.[/]",
                            title="[b]Tasks Require Manual Effort",
                        )
                    )
                else:
                    layout.update(
                        Panel(
                            f"[b i]Remaining {size} tasks require manual effort [/]: {':brick: ' * size}",
                            title="[b]Tasks Require Manual Effort",
                        )
                    )

    def _classify(self, done: Event) -> list[FeedBack]:
        """Classifies tasks that fail to validate."""

        finished, feedbacks = 0, []
        while finished < self.num_workers:
            feedback = self.feedback_queue.get()
            # The sentinel value 'None' is used to indicate worker has stopped
            if feedback is None:
                finished += 1
                continue

            feedbacks.append(feedback)

            if not feedback.result.distinguishable:
                self.console.print("Loading file: ", feedback.uid)
                book = self.software.load(feedback.uid)

                for sheet in book.sheets.values():
                    classifier = EquivalentClassChecker(
                        self.software, sheet, console=self.console, seed=42
                    )
                    classifier.loop()

                # update indistinguishable_counter
                with self.counter_lock:
                    self.counter.value -= 1

        done.set()
        self.console.print("Classification finished!")
        return feedbacks

    def _render(self):
        """Render validation and classification progress in the console."""

        # Event to notify that all indistinguishable tasks are classified
        done = Event()

        main_layout = Layout()
        validation_progress_layout = Layout(name="progress", size=3)
        manual_layout = Layout(name="manual", size=3)
        console_layout = Layout(name="console")
        main_layout.split_column(
            validation_progress_layout, manual_layout, console_layout
        )

        # setup progress panel
        validation_progress = Progress(
            "{task.description}",
            SpinnerColumn(),
            BarColumn(),
            "{task.completed}/{task.total}",
            "[progress.percentage]{task.percentage:>3.0f}%",
            TimeElapsedColumn(),
        )
        progress_task_id = validation_progress.add_task(
            "[cyan]Processing...",
            total=self.validation_task_queue.qsize() - self.num_workers,
        )
        validation_progress_layout.update(
            Panel(validation_progress, title="[b]Validation Progress")
        )

        # setup manual and console panel
        manual_layout.update(Panel("", title="[b]Tasks Require Manual Effort"))
        console_layout.update(Panel(self.console, title="[b]Classification Console"))

        with LivePro(main_layout, refresh_per_second=24) as live:
            self.console.set_live(live)

            t1 = Thread(
                target=self._render_validation_progress,
                args=(
                    validation_progress,
                    progress_task_id,
                ),
            )
            t2 = Thread(
                target=self._render_classfication_progress,
                args=(manual_layout, done),
            )

            t1.start()
            t2.start()
            # stuck here until all tasks are classified
            feedbacks = self._classify(done)
            t1.join()
            t2.join()
            self.console.print("[b]Congradulations! All tasks are classified![/]")
            return feedbacks

    def submit(self, task: Task):
        """Put a task into the task queue."""
        self.validation_task_queue.put(task)

    def run(
        self, task2feedback: Callable[[Task, SheetName, Result], FeedBack]
    ) -> list[FeedBack]:
        """Execute validator with an input-to-output transformation."""
        term = self._setup_term()
        # put sentinel value to indicate workers should stop
        for _ in range(self.num_workers):
            self.validation_task_queue.put(None)

        # Start worker processes first
        futures = [
            self.pool.submit(
                validate,
                self.software,
                self.validation_task_queue,
                self.feedback_queue,
                task2feedback,
                self.validation_progress_queue,
                self.counter,
                self.counter_lock,
                self.store_host,
                self.store_port,
            )
            for _ in range(self.num_workers)
        ]

        feedbacks = self._render()

        for future in futures:
            future.result()

        self._restore_term(term)
        return feedbacks

    def validate_large_dataset(self, sz: Optional[int] = None):
        """Validate a large dataset by loading sz items from the dataset.

        Args:
            sz: The number of items to load from the dataset. If None, all items will be loaded.
        """
        dataset = Dataset(self.software.name)
        cells = []
        for i, o in dataset.get_items(sz):
            ic, oc = Cell(content=i.decode()), Cell(content=o)
            cells.append((ic, oc))

        data = pd.DataFrame(cells, columns=[1, 2])
        sheet = Sheet(title=self.software.name, sheet=data)
        self.validate_large_sheet(sheet)

    def validate_large_sheet(self, sheet: Sheet):
        """Validate a large sheet."""
        classifier = EquivalentClassChecker(self.software, sheet)
        classifier.loop(parallel=True)

    def validate(
        self,
        path: Path | str,
        revalidate: bool = False,
    ):
        """Validate all spreadsheets in the given path.

        It can be a directory(id) or a single file(id). If it is a directory(id), all spreadsheets in the directory will be validated.

        This method will use a cache to track whether the spreadsheets have been modified since the last validation.
        If `revalidate` is set to `True`, the cache will be ignored, and all spreadsheets will be validated.
        Otherwise, only the spreadsheets that are either not in the cache or have been modified since the last validation
        will be validated.
        """
        if isinstance(self.software, Gsheet):
            client = BackOffClient.from_credential_path(self.software.credential_path)
            if client.is_folder_exists(path):
                files = client.list_spreadsheets(folder_id=path)
                for file in files:
                    task = ValidationTask(uid=file.id)
                    self.submit(task)

                feedbacks = self.run(validation_task2feedback)
            else:
                book = Book.from_gsheet(path)
                for sheet in book.sheets.values():
                    classfier = EquivalentClassChecker(self.software, sheet)
                    classfier.loop()

        elif isinstance(self.software, (Excel, Calc)):
            path = Path(path)
            if path.is_dir():
                config_dir = path / f".{__package__.split('.')[0]}"
                config_dir.mkdir(exist_ok=True)

                config_file = config_dir / f"{self.software.name}_validation_cache"

                if not revalidate and config_file.exists():
                    with config_file.open("r") as f:
                        cache = Cache.model_validate_json(f.read())
                else:
                    cache = Cache()

                # collect files needed to process
                for file in path.rglob("*"):
                    if (
                        file.is_file()
                        and file.suffix == self.software.suffix
                        and not any(part.startswith(".") for part in file.parts)
                    ):
                        if not cache.contains(file):
                            task = ValidationTask(uid=file)
                            self.submit(task)
                feedbacks = self.run(validation_task2feedback)
                # write back cache
                with config_file.open("w") as f:
                    for feedback in feedbacks:
                        cache.update(feedback.uid)
                    f.write(cache.model_dump_json())

            elif path.is_file():
                book = self.software.load(path.absolute())
                for sheet in book.sheets.values():
                    classfier = EquivalentClassChecker(self.software, sheet)
                    classfier.loop()
            else:
                raise FileNotFoundError(f"Path {path} does not exist.")
        else:
            raise NotImplementedError(f"Software {self.software} is not supported.")

    def _setup_term(self):
        fd = sys.stdin.fileno()
        oldterm = termios.tcgetattr(fd)
        newattr = termios.tcgetattr(fd)
        newattr[3] = newattr[3] & ~termios.ECHO
        termios.tcsetattr(fd, termios.TCSANOW, newattr)
        alt_screen_setup()
        return oldterm

    def _restore_term(self, term):
        fd = sys.stdin.fileno()
        termios.tcsetattr(fd, termios.TCSANOW, term)
        alt_screen_teardown()

    def __del__(self) -> None:
        self.pool.shutdown(wait=True)
