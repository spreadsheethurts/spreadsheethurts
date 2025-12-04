from pathlib import Path
import shutil
from typing import Optional
import logging
from zipfile import ZipFile
from io import BytesIO
import tempfile

import pandas as pd
import requests


from wizard.sheet import Book
from wizard.utils import get_logger
from .base import Software, EvaluationReturnType


class Excel(Software):
    """The Excel software."""

    def __init__(
        self,
        directory: Path,
        host: str = "localhost",
        port: str | int = 8000,
        single_path: str = "evaluate",
        batch_path: Optional[str] = "evaluate_batch",
        protocol: str = "http",
        logger: logging.Logger = get_logger(__name__),
        max_evaluations: int = 100_000,
    ) -> None:
        super().__init__(max_evaluations)
        directory.mkdir(exist_ok=True)
        self.directory = directory
        self.url = f"{protocol}://{host}:{port}"
        self.url_single = f"{self.url}/{single_path}"
        self.url_batch = f"{self.url}/{batch_path}" if batch_path else None
        self.logger = logger

    @property
    def name(self) -> str:
        return "excel"

    @property
    def suffix(self) -> str:
        return ".xlsx"

    def evaluate(
        self, book: Book, t: EvaluationReturnType = EvaluationReturnType.BOOK
    ) -> Book | Path:
        path = book.to_xlsx()

        with path.open(mode="rb") as f:
            response = requests.post(self.url_single, files={"file": f})
            if response.status_code != 200:
                raise ValueError(f"Failed to evaluate the file {path}")

            path = self.directory / path.name
            with path.open(mode="wb") as f:
                f.write(response.content)

        if t == EvaluationReturnType.UID:
            return path
        else:
            return Book.from_excel(path)

    def evaluate_batch(
        self, books: list[Book], t: EvaluationReturnType = EvaluationReturnType.BOOK
    ) -> list[Book | Path]:
        if not self.url_batch:
            return [self.evaluate(book, t) for book in books]

        file_handles = [open(book.to_xlsx(), "rb") for book in books]
        response = requests.post(
            self.url_batch,
            files=[("files", f) for f in file_handles],
        )

        if response.status_code != 200:
            raise ValueError("Failed to evaluate the files")

        # extract all files and rename them
        paths = []
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            # extract all files to the temporary directory
            with ZipFile(BytesIO(response.content)) as zipf:
                zipf.extractall(tmpdir)

                # rename all files
                for src in tmpdir.iterdir():
                    dst = self.directory / src.name
                    shutil.move(src, dst)
                    paths.append(dst)

        if t == EvaluationReturnType.UID:
            return paths
        else:
            return [Book.from_excel(path) for path in paths]

    def is_encoding_eq(self, e1: pd.Series, e2: pd.Series) -> bool:
        if e1.index.equals(e2.index) and e1.equals(e2):
            return True
        elif e1["number"] and e2["datetime"]:
            return True
        elif e2["number"] and e1["datetime"]:
            return True

        return False

    def load(self, uid: Path | str) -> Book:
        return Book.from_excel(uid)
