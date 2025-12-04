import pytest
from typing import Optional

from wizard.features.calc.datetime_alike.utils import DateTimeUtils, Month2Num


class TestMonth2Num:
    @pytest.fixture
    def month2num(self):
        return Month2Num()

    @pytest.fixture
    def valid_months(self) -> list[tuple[str, int]]:
        return [("January", 1), (1, 1), ("01", 1), ("Jan", 1), ("Jan.", 1)]

    @pytest.fixture
    def invalid_months(self) -> list[str]:
        return ["January.", "001", "0", 0]

    def test_valid_month(self, month2num: Month2Num, valid_months):
        for month, expected in valid_months:
            assert month2num(month) == expected

    def test_invalid_month(self, month2num: Month2Num, invalid_months):
        for month in invalid_months:
            assert month2num(month) is None


class TestDateTimeUtils:
    @pytest.fixture
    def utils(self):
        return DateTimeUtils()

    @pytest.mark.parametrize(
        "year, expected",
        [
            ("0", 2000),
            ("00", 2000),
            ("000", None),
            ("001", 1),
            ("30", 1930),
            ("030", 30),
            ("99", 1999),
            ("2024", 2024),
            ("000042", 42),
            ("1000000", 16960),
            ("32768", None),
        ],
    )
    def test_get_year(self, utils: DateTimeUtils, year: str, expected: Optional[int]):
        assert utils.get_year(year) == expected

    @pytest.mark.parametrize(
        "day, expected",
        [
            ("1", 1),
            ("01", 1),
            ("31", 31),
            ("031", None),
            ("32", None),
            ("032", None),
            ("001", None),
        ],
    )
    def test_get_day(self, utils: DateTimeUtils, day: str, expected: Optional[int]):
        assert utils.get_day(day) == expected
