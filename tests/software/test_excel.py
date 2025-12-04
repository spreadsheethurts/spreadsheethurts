from pathlib import Path
from datetime import date

import pandas as pd
import pytest

from wizard.cell import Cell
from wizard.software.excel import Excel


@pytest.fixture(scope="session")
def dummy_excel():
    return Excel("host", "port", Path("/tmp"), "single")


def assert_type(series: pd.Series, type: str):
    for index, value in series.items():
        if index == type:
            assert value
        else:
            assert not value


def test_encode_type(dummy_excel: Excel):
    integer = Cell(value=1)
    error = Cell(value="#DIV/0!")
    text = Cell(value="hello world")
    datetime = Cell(value=date.today())
    bool = Cell(value=True)

    assert_type(dummy_excel.encode_type(integer), "number")
    assert_type(dummy_excel.encode_type(error), "error")
    assert_type(dummy_excel.encode_type(text), "text")
    assert_type(dummy_excel.encode_type(datetime), "datetime")
    assert_type(dummy_excel.encode_type(bool), "bool")


def test_is_encoding_eq(dummy_excel: Excel):
    integer = dummy_excel.encode_type(Cell(value=1))
    float = dummy_excel.encode_type(Cell(value=1.0))
    datetime = dummy_excel.encode_type(Cell(value=date.today()))
    assert dummy_excel.is_encoding_eq(integer, float)
    assert dummy_excel.is_encoding_eq(integer, datetime)

    error1 = dummy_excel.encode_type(Cell(value="#DIV/0!"))
    error2 = dummy_excel.encode_type(Cell(value="#NAME?"))
    assert dummy_excel.is_encoding_eq(error1, error2)

    string1 = dummy_excel.encode_type(Cell(value="hello world"))
    string2 = dummy_excel.encode_type(Cell(value="Hello World"))
    assert dummy_excel.is_encoding_eq(string1, string2)

    true = dummy_excel.encode_type(Cell(value=True))
    false = dummy_excel.encode_type(Cell(value=False))
    assert dummy_excel.is_encoding_eq(true, false)

    assert not dummy_excel.is_encoding_eq(integer, error1)
    assert not dummy_excel.is_encoding_eq(datetime, string1)
    assert not dummy_excel.is_encoding_eq(true, error1)
