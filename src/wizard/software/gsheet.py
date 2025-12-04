from pathlib import Path
import os
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed


from wizard.sheet import Book
from wizard.software.base import EvaluationReturnType
from .base import Software


def evaluate(
    folder_id, book: Book, t: EvaluationReturnType = EvaluationReturnType.BOOK
) -> Book | Path:
    range_format = {"A:A": {"numberFormat": {"type": "TEXT"}}}
    id = book.to_gsheet(folder_id, range_format=range_format)
    if t == EvaluationReturnType.UID:
        return id
    else:
        return Book.from_gsheet(id, load_formula=False)


class Gsheet(Software):
    """The GoogleDoc software.

    Please ensure envrionment variable `GOOGLE_CREDENTIAL_PATH` is set to the path of the service account key.
    """

    def __init__(
        self,
        folder_id: Optional[str] = None,
        max_worker_num: Optional[int] = None,
        credential_path: Optional[str] = None,
        max_evaluations: int = 100_000,
    ) -> None:
        super().__init__(max_evaluations)

        self.folder_id = folder_id
        self.pool = ThreadPoolExecutor(max_worker_num)
        if not credential_path:
            credential_path = os.environ["GOOGLE_CREDENTIAL_PATH"]

        self.credential_path = credential_path

    @property
    def name(self) -> str:
        return "gsheet"

    @property
    def suffix(self) -> str:
        return ".gsheet"

    def evaluate(
        self, book: Book, t: EvaluationReturnType = EvaluationReturnType.BOOK
    ) -> Book | Path:
        return evaluate(self.folder_id, book, t)

    def evaluate_batch(
        self, books: list[Book], t: EvaluationReturnType = EvaluationReturnType.BOOK
    ) -> list[Book | Path]:
        tasks = [self.pool.submit(evaluate, self.folder_id, book, t) for book in books]
        return [task.result() for task in as_completed(tasks)]

    def get_url(self, uid: str) -> str:
        return f"https://docs.google.com/spreadsheets/d/{uid}"

    def __del__(self) -> None:
        self.pool.shutdown()

    def load(self, uid: Path | str) -> Book:
        return Book.from_gsheet(uid)
