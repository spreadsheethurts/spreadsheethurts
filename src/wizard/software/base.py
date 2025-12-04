from enum import Enum
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Iterable
import uuid
import tempfile
from contextlib import contextmanager
import shutil

import pandas as pd

from wizard.sheet import Book, Sheet
from wizard.cell import Cell, DataType


class EvaluationReturnType(Enum):
    """The return type of the evaluation."""

    BOOK = "book"
    UID = "uid"


TYPES = ["number", "datetime", "bool", "error", "text"]


@contextmanager
def tempdir_removed_after_return():
    """Provides a temporary directory that is deleted *after* its context is exited."""

    temp_dir = tempfile.mkdtemp()
    try:
        yield temp_dir
    finally:
        # This code runs after the 'with' block is fully exited
        shutil.rmtree(temp_dir)


class Software(ABC):

    def __init__(self, max_evaluations: int = 100_000):
        self.max_evaluations = max_evaluations

    def unique_name(self) -> str:
        return str(uuid.uuid4())

    @property
    @abstractmethod
    def name(self) -> str:
        """The name of the software."""

    @property
    @abstractmethod
    def suffix(self) -> str:
        """The suffix of the software, including the preceding dot."""

    @abstractmethod
    def evaluate(
        self, book: Book, t: EvaluationReturnType = EvaluationReturnType.BOOK
    ) -> Book | Path:
        """Evaluate the formulas in the spreadsheet."""

    @abstractmethod
    def evaluate_batch(
        self, books: list[Book], t: EvaluationReturnType = EvaluationReturnType.BOOK
    ) -> list[Book | Path]:
        """Evaluate the formulas in the spreadsheets in batch."""

    def evaluate_text(self, input: str) -> Any:
        """Evaluate a single text input to determine its data type and value.

        This method simulates how the software would typecast a value when a user types it into a cell.
        """
        name = self.unique_name()
        cell = Cell(value=input)
        data = pd.DataFrame([[cell, cell]])
        sheet = Sheet(title="Sheet1", sheet=data)
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.evaluate(
                sheet.to_book(Path(temp_dir) / (name + self.suffix)),
                EvaluationReturnType.BOOK,
            )
        return result.sheets["Sheet1"].sheet.iloc[0, 1].content

    def evaluate_texts(self, inputs: Iterable[str]) -> list[Any]:
        """Evaluate multiple text inputs to determine their data types and values."""
        inputs = list(inputs)
        results = []
        for i in range(0, len(inputs), self.max_evaluations):
            batch = inputs[i : i + self.max_evaluations]
            name = self.unique_name()
            data = pd.DataFrame(
                [[Cell(value=input), Cell(value=input)] for input in batch]
            )
            sheet = Sheet(title="Sheet1", sheet=data)
            with tempfile.TemporaryDirectory() as temp_dir:
                result = self.evaluate(
                    sheet.to_book(Path(temp_dir) / (name + self.suffix)),
                    EvaluationReturnType.BOOK,
                )
            results.extend(
                cell.content for cell in result.sheets["Sheet1"].sheet.iloc[:, 1]
            )
        return results

    def evaluate_texts_batch(
        self,
        batch: list[list[str]],
        t: EvaluationReturnType = EvaluationReturnType.BOOK,
    ) -> list[Book | Path | str]:
        """Evaluate a batch of texts."""
        with tempdir_removed_after_return() as temp_dir:
            books = []
            for inputs in batch:
                name = self.unique_name()
                data = pd.DataFrame(
                    [[Cell(value=input), Cell(value=input)] for input in inputs]
                )
                book = Sheet(title="Sheet1", sheet=data).to_book(
                    Path(temp_dir) / (name + self.suffix)
                )
                books.append(book)

            return self.evaluate_batch(books, t)

    def encode_type(self, cell: Cell) -> pd.Series:
        """Encode the cell according to the software type system."""
        encoding = pd.Series([False] * self.encoding_size, index=self.types, dtype=bool)
        match cell.datatype:
            case DataType.INTEGER | DataType.FLOAT:
                encoding["number"] = True
            case DataType.DATETIME:
                encoding["datetime"] = True
            case DataType.BOOL:
                encoding["bool"] = True
            case DataType.ERROR:
                encoding["error"] = True
            case DataType.STRING | DataType.INLINESTRING:
                encoding["text"] = True
            case DataType.NONE:
                pass
            case _:
                # TODO(gpl): figure out how many types are there
                breakpoint()

        return encoding

    def is_encoding_eq(self, e1: pd.Series, e2: pd.Series) -> bool:
        """Apply encoding comparison rules accoring to the software data conversion semantic."""
        if e1.index.equals(e2.index) and e1.equals(e2):
            return True

        return False

    @property
    def encoding_size(self) -> int:
        """Return the size of the encoding type."""
        return len(self.types)

    @property
    def types(self) -> list[str]:
        """Returns the type names used for encoding."""
        return TYPES

    @abstractmethod
    def load(self, uid: Path | str) -> Book:
        """Load the spreadsheet."""
