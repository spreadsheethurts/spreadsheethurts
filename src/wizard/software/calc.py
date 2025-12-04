from pathlib import Path
from typing import Optional
import logging
from zipfile import ZipFile
from io import BytesIO
import tempfile
import os
import requests
import shutil

from wizard.sheet import Book
from wizard.utils import get_logger
from .base import Software, EvaluationReturnType


class Calc(Software):
    def __init__(
        self,
        directory: Path,
        host: str = "localhost",
        port: int = 8000,
        single_path: str = "evaluate",
        batch_path: Optional[str] = "evaluate_batch",
        protocol: str = "http",
        logger: logging.Logger = get_logger(__name__),
        max_evaluations: int = 100_000,
    ):
        super().__init__(max_evaluations)
        directory.mkdir(exist_ok=True)
        self.directory = directory
        self.url = f"{protocol}://{host}:{port}"
        self.url_single = f"{self.url}/{single_path}"
        self.url_batch = f"{self.url}/{batch_path}" if batch_path else None
        self.logger = logger

    @property
    def name(self) -> str:
        return "calc"

    @property
    def suffix(self) -> str:
        return ".ods"

    def evaluate(
        self, book: Book, t: EvaluationReturnType = EvaluationReturnType.BOOK
    ) -> Book | Path:
        path = book.to_ods()

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
            return Book.from_calc(path)

    def evaluate_batch(
        self, books: list[Book], t: EvaluationReturnType = EvaluationReturnType.BOOK
    ) -> list[Book | Path]:
        if not self.url_batch:
            return [self.evaluate(book, t) for book in books]
        file_handles = [open(book.to_ods(), "rb") for book in books]

        # Split files into batches of 1000
        batch_size = 1000
        paths = []
        for i in range(0, len(file_handles), batch_size):
            batch = file_handles[i : i + batch_size]

            # Calculate total size of files in batch
            batch_size_bytes = sum(os.path.getsize(f.name) for f in batch)
            batch_size_mb = batch_size_bytes / (1024 * 1024)
            self.logger.info(
                f"Sending batch {i//batch_size} with size: {batch_size_mb:.2f} MB"
            )

            response = requests.post(
                self.url_batch,
                files=[("files", f) for f in batch],
            )

            if response.status_code != 200:
                raise ValueError(
                    f"Failed to evaluate batch {i//batch_size}, {response.content}"
                )

            # extract all files and rename them
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
            return [Book.from_calc(path) for path in paths]

    def load(self, uid: Path | str) -> Book:
        return Book.from_calc(uid)
