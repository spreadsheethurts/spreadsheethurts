import pytest
from pathlib import Path
from datetime import datetime
import random
import pandas as pd


from wizard import Book, Cell, Sheet


@pytest.fixture(scope="session")
def spreadsheet(request: pytest.FixtureRequest, _setup_and_teardown):
    data = pd.DataFrame(
        [
            (
                Cell(value="hello", row=1, column=1, datatype="s"),
                Cell(value="hello", row=1, column=2, datatype="s"),
            ),
            (
                Cell(value="1", row=2, column=1, datatype="n"),
                Cell(value=1, row=2, column=2, datatype="n"),
            ),
            (
                Cell(value="True", row=3, column=1, datatype="b"),
                Cell(value=True, row=3, column=2, datatype="b"),
            ),
            (
                Cell(value="2024-01-01", row=4, column=1, datatype="d"),
                Cell(value=datetime(2024, 1, 1), row=4, column=2, datatype="d"),
            ),
        ],
        columns=[0, 1],
    )
    sheet = Sheet(title="title", sheet=data)
    return sheet.to_book()


@pytest.fixture(scope="session")
def sheet(spreadsheet: Book):
    return spreadsheet.active_sheet


@pytest.fixture(scope="session")
def _setup_and_teardown():
    # setup
    yield
    # teardown


@pytest.fixture(scope="session")
def none() -> Cell:
    return Cell(row=1, column=1, value=None, datatype="n", dataformat="General")


@pytest.fixture(scope="session")
def month_names() -> list[str]:
    return [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]


@pytest.fixture(scope="session")
def month_numbers() -> list[int]:
    return list(range(1, 13))


@pytest.fixture(scope="session")
def days_leap() -> list[int]:
    return [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


@pytest.fixture(scope="session")
def days() -> list[int]:
    return [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


@pytest.fixture(scope="session")
def years() -> list[int]:
    return list(range(1, 3000 + 1))


@pytest.fixture(scope="session")
def month_name_days(month_names, days) -> list[Cell]:
    seps = [" ", "/", "-"]

    prefix = " " * random.randint(0, 100)
    suffix = " " * random.randint(0, 100)

    return [
        Cell(value=f"{month[:length]}{prefix}{sep}{suffix}{day}", datatype="s")
        for sep in seps
        for idx, month in enumerate(month_names)
        for day in range(1, days[idx] + 1)
        for length in range(3, len(month) + 1)
    ]


@pytest.fixture(scope="session")
def day_month_names(month_names, days) -> list[Cell]:
    seps = [" ", "/", "-", ""]

    prefix = " " * random.randint(0, 100)
    suffix = " " * random.randint(0, 100)

    return [
        Cell(value=f"{day}{prefix}{sep}{suffix}{month[:length]}", datatype="s")
        for sep in seps
        for idx, month in enumerate(month_names)
        for day in range(1, days[idx] + 1)
        for length in range(3, len(month) + 1)
    ]


@pytest.fixture(scope="session")
def month_number_days(month_numbers, days) -> list[Cell]:
    seps = ["/", "-"]

    prefix = " " * random.randint(0, 100)
    suffix = " " * random.randint(0, 100)

    return [
        Cell(value=f"{month}{prefix}{sep}{suffix}{day}", datatype="s")
        for sep in seps
        for idx, month in enumerate(month_numbers)
        for day in range(1, days[idx] + 1)
    ]


@pytest.fixture(scope="session")
def day_month_numbers(month_numbers, days) -> list[Cell]:
    seps = ["/", "-"]

    prefix = " " * random.randint(0, 100)
    suffix = " " * random.randint(0, 100)

    return [
        Cell(value=f"{day}{prefix}{sep}{suffix}{month}", datatype="s")
        for sep in seps
        for idx, month in enumerate(month_numbers)
        for day in range(1, days[idx] + 1)
    ]


@pytest.fixture(scope="session")
def year_month_number_days(years, month_numbers, days) -> list[Cell]:
    seps = ["/", "-"]

    prefix = " " * random.randint(0, 100)
    suffix = " " * random.randint(0, 100)

    return [
        Cell(value=f"{year}{prefix}{sep}{suffix}{month}{sep}{day}", datatype="s")
        for sep in seps
        for year in years
        for idx, month in enumerate(month_numbers)
        for day in range(1, days[idx] + 1)
    ]
