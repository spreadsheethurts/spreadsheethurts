from __future__ import annotations
import datetime
from enum import StrEnum, unique
from typing import Optional, Self, Any, Union, Literal
import string

from pydantic import Field, computed_field
from openpyxl.cell.cell import Cell as OpenpyxlCell
from openpyxl.worksheet.formula import ArrayFormula
from ezodf.cells import Cell as OdsCell

from wizard.base import Serializable
from wizard.utils import resolve_ezodf_to_python
from wizard.typ.datetime import DateTime, GregorianDateTime, ExcelDateTime

# BigDateTime must be listed first in the Union since it inherits from datetime.datetime.
# This prevents pydantic from coercing BigDateTime instances into datetime.datetime,
# which would cause overflow errors for large dates.
DATETIME = Union[
    GregorianDateTime,
    ExcelDateTime,
    DateTime,
    datetime.datetime,
    datetime.date,
    datetime.time,
    datetime.timedelta,
]
DATATYPE = str | bool | int | float | DATETIME | None


@unique
class DataType(StrEnum):
    INTEGER = "i"
    FLOAT = "f"
    COMPLEX = "c"
    STRING = "s"
    DATETIME = "d"
    BOOL = "b"
    ERROR = "e"

    INLINESTRING = "inlineStr"

    NUMBER = "n"
    NONE = "none"


error_codes = ("#NULL!", "#DIV/0!", "#VALUE!", "#REF!", "#NAME?", "#NUM!", "#N/A")
type_mapping = {
    int: DataType.INTEGER,
    float: DataType.FLOAT,
    complex: DataType.COMPLEX,
    str: DataType.STRING,
    bool: DataType.BOOL,
    datetime.datetime: DataType.DATETIME,
    datetime.date: DataType.DATETIME,
    datetime.time: DataType.DATETIME,
    datetime.timedelta: DataType.DATETIME,
    DateTime: DataType.DATETIME,
    GregorianDateTime: DataType.DATETIME,
    ExcelDateTime: DataType.DATETIME,
    type(None): DataType.NONE,
    DataType.STRING: str,
    DataType.INTEGER: int,
    DataType.FLOAT: float,
    DataType.COMPLEX: complex,
    DataType.BOOL: bool,
    DataType.DATETIME: datetime.datetime,
    DataType.ERROR: str,
}


class Cell(Serializable):
    """Cell represents a cell in a spreadsheet.

    Ensures content and datatype remain consistently synchronized. Modifying
    the datatype automatically updates the content accordingly, and vice versa.
    """

    row: int = Field(default=1, exclude=True)
    column: int = Field(default=1, exclude=True)
    dataformat: str = Field(default="General", exclude=True)
    formula: Optional[str] = Field(default=None)
    parent: Optional[Sheet] = Field(default=None, exclude=True, repr=False)
    content: str | bool | int | float | DATETIME | None = Field(alias="value")
    loaded_datatype: Optional[DataType] = Field(default=None, exclude=True, repr=False)

    @computed_field
    @property
    def datatype(self) -> DataType:
        if isinstance(self.content, str) and self.content in error_codes:
            return DataType.ERROR
        else:
            return type_mapping[type(self.content)]

    @datatype.setter
    def datatype(self, value: DataType):
        assert value != DataType.ERROR
        self.content = type_mapping[value](self.content)

    def is_formula(self):
        return self.formula is not None

    @property
    def column_letter(self):
        return string.ascii_uppercase[self.column - 1]

    @property
    def location(self) -> str:
        return f"{self.column_letter}{self.row}"

    @classmethod
    def from_excel(
        cls,
        dcell: OpenpyxlCell,
        fcell: OpenpyxlCell,
        parent: Optional[Sheet] = None,
        base: Literal["1900", "1904"] = "1900",
    ):
        """Load a cell from data cell and formula cell."""
        value = dcell.value
        if isinstance(value, datetime.datetime):
            try:
                value = ExcelDateTime.from_datetime(value)
            except OverflowError:
                # small or large datetime values will be displayed as #####, we convert it to float/int
                base = (
                    datetime.datetime(1900, 1, 1)
                    if base == "1900"
                    else datetime.datetime(1904, 1, 1)
                )
                timedelta = value - base + datetime.timedelta(days=1)
                value = ExcelDateTime.timedelta_to_number(timedelta)

        elif isinstance(value, datetime.timedelta):
            if base == "1900":
                try:
                    value = (
                        ExcelDateTime(1900, 1, 1) + value - datetime.timedelta(days=1)
                    )
                # small or large datetime values will be displayed as #####, we convert it to float/int
                except OverflowError:
                    value = ExcelDateTime.timedelta_to_number(value)
            else:
                value = ExcelDateTime(1904, 1, 1) + value - datetime.timedelta(days=1)

        cell = cls(
            row=dcell.row,
            column=dcell.column,
            content=value,
            dataformat=dcell.number_format,
            parent=parent,
            loaded_datatype=DataType(dcell.data_type),
        )
        if fcell.data_type == "f":
            if isinstance(fcell.value, ArrayFormula):
                # currently treat array formulas as strings starting with "="
                cell.content = fcell.value.text
            else:
                cell.formula = fcell.value

        return cell

    @classmethod
    def from_ods(cls, cell: OdsCell, parent: Optional[Sheet] = None) -> Self:
        value = resolve_ezodf_to_python(cell.value, cell.value_type)
        return cls(value=value, parent=parent, formula=cell.formula)

    @classmethod
    def from_gsheet(
        cls, value: Any, fvalue: Any = None, parent: Optional[Sheet] = None
    ) -> Self:
        cell = cls(content=value, parent=parent)
        if fvalue is not None and value != fvalue:
            cell.formula = fvalue
        return cell

    def is_empty(self):
        return self.content is None or self.content == ""

    def __rich__(self) -> str:
        if self.is_formula():
            return f"{self.content}({self.formula})"
        elif isinstance(self.content, str) and self.content.isspace():
            return r"[yellow](WHITESPACE)"
        elif self.content == "":
            return r"[yellow](EMPTY STRING)"
        elif self.content is None:
            return r"[yellow](NONE)"

        return str(self.content)

    def __repr__(self) -> str:
        return f"Cell(value={self.content})"

    @classmethod
    def make_empty(cls, row: int = 1, column: int = 1, parent: Optional[Sheet] = None):
        return cls(row=row, column=column, content="", parent=parent)

    def __hash__(self) -> int:
        return hash(self.content)

    @classmethod
    def from_formula(cls, formula: str) -> Self:
        return cls(content=None, formula=formula)


from .sheet import Sheet  # noqa: E402

Cell.model_rebuild()
