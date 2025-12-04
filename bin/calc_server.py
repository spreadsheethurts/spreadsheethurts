# This script is intended for use exclusively on Linux-based systems with LibreOffice installed.
# Installing the UNO module for a custom Python interpreter (such as a conda environment or virtualenv) is a common requirement.
# However, on macOS, this process is not straightforward. The UNO module is bundled with LibreOffice's built-in Python interpreter,
# making it more complex to change the Python interpreter compared to Linux-based systems. For more details, see this Stack Overflow
# post: https://stackoverflow.com/questions/15223209/installing-pyuno-libreoffice-for-private-python-build#19158549.
import sys
import os
import signal
import itertools
from sys import platform
import time
from typing import Optional, Annotated
import subprocess
import logging
from pathlib import Path
import shutil
from zipfile import ZipFile
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import Manager, Lock
from queue import Queue
from ctypes import c_int

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
from rich.logging import RichHandler
from rich.progress import Progress
import typer

# Add the path to the UNO module
# Option1: The UNO module can be installed on Ubuntu using the command: `sudo apt install python3-uno` (usually the version is late)
# Option2: Download the latest libreoffice and add the path, in this example "/opt/libreoffice24.8/program"
# Note: We disable the formatter to prevent "import uno" from being moved to the top of the file.
# fmt: off
LIBREOFFCE_PATH = "/opt/libreoffice24.8"
LIBREOFFCE_PROGRAM_PATH = f"{LIBREOFFCE_PATH}/program"
sys.path.insert(0 , LIBREOFFCE_PROGRAM_PATH)
os.environ["UNO_PATH"] = LIBREOFFCE_PROGRAM_PATH
os.environ["URE_BOOTSTRAP"] = f"vnd.sun.star.pathname:{LIBREOFFCE_PROGRAM_PATH}/fundamentalrc"
import uno
from unohelper import systemPathToFileUrl
from com.sun.star.beans import PropertyValue
from com.sun.star.connection import NoConnectException
# fmt: on


def retry(
    delays=(0, 1, 5, 30, 180, 600, 3600), exception=Exception, report=lambda *args: None
):
    """Simple retry decorator for functions that may raise exceptions.
    Credit:
    http://code.activestate.com/recipes/580745-retry-decorator-in-python/
    """

    def wrapper(function):
        def wrapped(*args, **kwargs):
            problems = []
            for delay in itertools.chain(delays, [None]):
                try:
                    return function(*args, **kwargs)
                except exception as problem:
                    problems.append(problem)
                    if delay is None:
                        report("retryable failed definitely:", problems)
                        raise
                    else:
                        report(
                            "retryable failed:", problem, "-- delaying for %ds" % delay
                        )
                        time.sleep(delay)
            return None

        return wrapped

    return wrapper


def terminate_daemon(daemon: subprocess.Popen):
    if platform.startswith("win") or platform == "darwin":
        daemon.terminate()
    elif platform == "linux":
        os.killpg(os.getpgid(daemon.pid), signal.SIGTERM)


def bootstrap(soffice: str, connect_string: str, headless: bool, delays=(1, 3, 5, 7)):
    """Start the soffice daemon and connect to it."""
    try:
        cmd = [
            "sudo",
            soffice,
            "-env:SingleAppInstance=false",
            "--accept=" + f'"{connect_string}"',
        ]
        if headless:
            cmd.append("--headless")

        cmd = " ".join(cmd)
        print(f"Starting LibreOffice with command: {cmd}")

        if platform.startswith("win") or platform == "darwin":
            daemon = subprocess.Popen(cmd, shell=True)
        elif platform == "linux":  # Use a process group to enable proper termination
            daemon = subprocess.Popen(cmd, shell=True, preexec_fn=os.setsid)
        else:
            raise OSError

        local_context = uno.getComponentContext()
        resolver = local_context.ServiceManager.createInstanceWithContext(
            "com.sun.star.bridge.UnoUrlResolver", local_context
        )
        connection = "uno:" + connect_string + "StarOffice.ComponentContext"

        @retry(delays=delays, exception=NoConnectException, report=print)
        def resolve():
            return resolver.resolve(connection)

        ctx = resolve()
        return (
            daemon,
            ctx.ServiceManager.createInstanceWithContext(
                "com.sun.star.frame.Desktop", ctx
            ),
        )

    except Exception as e:
        time.sleep(3)
        terminate_daemon(daemon)
        raise ValueError(f"Failed to connect to LibreOffice, {e}")


def worker(
    queue: Queue,
    logger: logging.Logger,
    soffice: str,
    connect_string: str,
    headless: bool,
    finished: c_int,
    finished_lock: Lock,
    column: int = 1,
):
    """A worker that fetches tasks from the queue and evaluates the specified column in ODS files with a launched LibreOffice Calc instance."""

    daemon, desktop = bootstrap(soffice, connect_string, headless)
    logger.info(f"Worker {os.getpid()} with {connect_string} started")

    if headless:
        properties = (PropertyValue(Name="Hidden", Value=True),)
    else:
        properties = ()

    while True:
        file = queue.get()
        if file is None:
            break

        try:
            file_url = systemPathToFileUrl(str(file))
            # Open the document
            spreadsheet = desktop.loadComponentFromURL(
                file_url, "_blank", 0, tuple(properties)
            )

            # Retrieve the sheet data, apply the General number format, and reinsert the sheet data
            for idx in range(spreadsheet.Sheets.Count):
                sheet = spreadsheet.Sheets.getByIndex(idx)
                cell_range = sheet.getCellRangeByPosition(
                    column, 0, column, sheet.Rows.Count - 1
                )

                data_array = cell_range.getDataArray()

                # Apply the number format "General"
                # In LibreOffice, number format "General" corresponds to number format key 0
                num_format_key = 0
                cell_range.NumberFormat = num_format_key

                # Set the formulas (or values) back into the target range
                cell_range.setFormulaArray(data_array)

            # Close and save the document
            spreadsheet.storeAsURL(file_url, ())
            # The close method is necessary to close the document and free up memory.
            spreadsheet.close(True)

            queue.task_done()

            with finished_lock:
                finished.value += 1
        except uno.com.sun.star.uno.RuntimeException:
            logger.error(
                f"Uno runtime error occurred while processing {file}, put file back to the queue and restart the daemon"
            )
            terminate_daemon(daemon)
            daemon, desktop = bootstrap(soffice, connect_string, headless)
            queue.put(file)

            with finished_lock:
                finished.value -= 1
        except Exception as e:
            logger.error(
                f"Occured error {e} while processing {file}, put file back to the queue"
            )
            queue.put(file)

            with finished_lock:
                finished.value -= 1

    terminate_daemon(daemon)


class Calc:
    """Launch multiple LibreOffice Calc instances to evaluate a specified column in ODS files.

    Spawns one LibreOffice Calc instance per CPU core to process and evaluate the specified column in ODS files in parallel.
    This script must be run with elevated privileges because concurrent access to LibreOffice Calc is not supported in standard
    desktop mode, due to the UNO object model not supporting pickling, which makes multiprocessing difficult without separate instances.

    Args:
        logger (logging.Logger): Logger instance for capturing process details.
        host (str): Host to bind to (default: "localhost").
        base_port (int): Base port used to assign ports for launching multiple LibreOffice Calc instances (default: 21345).
        column (int): One-based index of the column to process (default: 2).
        soffice (str): Path to the `soffice` executable (default: None).
        headless (bool): Whether to run LibreOffice in headless mode (default: True).
    """

    def __init__(
        self,
        logger: logging.Logger,
        host: str = "localhost",
        base_port: int = 21345,
        column: int = 2,
        soffice: Optional[str] = None,
        headless: bool = True,
    ):
        self.logger = logger
        self.soffice = self._resolve_soffice(soffice)
        self.logger.info(f"Resolve soffice to {self.soffice}")

        self.executor = ProcessPoolExecutor(max_workers=os.cpu_count())
        self.queue = Manager().Queue()
        self.finished = Manager().Value(c_int, 0)
        self.finished_lock = Manager().Lock()
        self.workers = [
            self.executor.submit(
                worker,
                self.queue,
                self.logger,
                self.soffice,
                f"socket,host={host},port={base_port + i};urp;",
                headless,
                self.finished,
                self.finished_lock,
                column - 1,  # Convert to 0-based index
            )
            for i in range(os.cpu_count())
        ]

    def _resolve_soffice(self, soffice: Optional[str] = None):
        """Try the best to resolve the path to the soffice executable."""
        if soffice is None:
            if "UNO_PATH" in os.environ:
                soffice = os.environ["UNO_PATH"]
            else:
                soffice = ""  # let's hope for the best
            soffice = os.path.join(soffice, "soffice")
            if platform.startswith("win"):
                soffice += ".exe"
                soffice = '"' + soffice + '"'  # accommodate ' ' spaces in filename
            elif platform == "darwin":  # any other un-hardcoded suggestion?
                soffice = "/Applications/LibreOffice.App/Contents/MacOS/soffice"
        return soffice

    @classmethod
    def from_socket(cls, logger, host: str = "localhost", port: int = 21345, **kwargs):
        """Create a Calc instance via socket connection."""
        return cls(logger, host=host, base_port=port, **kwargs)

    def evaluate(self, *files: Path, hidden=True):
        for file in files:
            self.queue.put(file)

        total = len(files)
        with Progress() as progress:
            task = progress.add_task("Evaluating files...", total=total)
            while self.finished.value < total:
                with self.finished_lock:
                    progress.update(task, completed=self.finished.value)
                time.sleep(0.1)

            self.logger.info("All tasks completed")

        self.queue.join()

    def __del__(self):
        for _ in self.workers:
            self.queue.put(None)
        self.executor.shutdown(wait=True)


def main(
    column: Annotated[
        int, typer.Option("--column", "-c", help="The column to evaluate (one based).")
    ] = 2,
    host: Annotated[
        str, typer.Option("--host", "-h", help="The host to bind to.")
    ] = "0.0.0.0",
    port: Annotated[
        int, typer.Option("--port", "-p", help="The port to bind to.")
    ] = 8000,
    soffice: Annotated[
        Optional[str],
        typer.Option("--soffice", "-s", help="The soffice executable path."),
    ] = None,
    directory: Annotated[
        str,
        typer.Option(
            "--directory",
            "-d",
            help="The directory to store the evaluated files.",
        ),
    ] = "server_datasets",
    max_batch_num: Annotated[
        int,
        typer.Option(
            "--max-batch-num",
            "-m",
            help="The maximum number of files to evaluate in a batch.",
        ),
    ] = 20,
):
    logging.basicConfig(
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, markup=True)],
    )

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    wd = Path.cwd() / directory
    wd.mkdir(exist_ok=True)

    calc = Calc.from_socket(logger, column=column, soffice=soffice)
    app = FastAPI()

    @app.get("/")
    def root():
        return "Calc Server"

    @app.post("/evaluate")
    def evaluate(file: UploadFile = File(...)):
        path = wd / file.filename
        with path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        calc.evaluate(path)

        return FileResponse(path, filename=file.filename)

    @app.post("/evaluate_batch")
    def evaluate_batch(files: list[UploadFile] = File(...)):
        dir = wd / str(time.time())
        dir.mkdir(exist_ok=True)
        paths = [dir / file.filename for file in files]
        for path, file in zip(paths, files):
            with open(path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

        logger.info(f"Evaluating {len(paths)} files...")
        calc.evaluate(*paths)

        zipped_basename = "evaluated_files.zip"
        zipped_path = wd / zipped_basename

        with ZipFile(zipped_path, "w") as zipf:
            for path in paths:
                zipf.write(path, arcname=path.name)

        return FileResponse(
            zipped_path, media_type="application/zip", filename=zipped_basename
        )

    import uvicorn

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    typer.run(main)
