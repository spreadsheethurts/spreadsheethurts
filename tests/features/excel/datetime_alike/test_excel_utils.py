import pytest
from typing import Optional

from wizard.features.excel.datetime_alike.utils import DateTimeUtils, Month2Num


class TestMonth2Num:
    @pytest.fixture
    def month2num(self):
        return Month2Num()

    @pytest.fixture
    def valid_months(self) -> list[tuple[str, int]]:
        jan = "January"
        return [(1, 1), ("01", 1)] + [(jan[:i], 1) for i in range(3, len(jan) + 1)]

    @pytest.fixture
    def invalid_months(self) -> list[str]:
        return ["001", "0", 0, 13]

    def test_valid_month(self, month2num: Month2Num, valid_months):
        for month, expected in valid_months:
            assert month2num[month] == expected

    def test_invalid_month(self, month2num: Month2Num, invalid_months):
        for month in invalid_months:
            assert month2num[month] is None


class TestDateTimeUtils:
    @pytest.fixture
    def utils(self):
        return DateTimeUtils()

    @pytest.mark.parametrize(
        "year, expected",
        [
            ("1900", 1900),
            ("1901", 1901),
            ("1902", 1902),
            ("01", 2001),
            ("30", 1930),
            ("0", 2000),
            ("0000", None),
            ("000", None),
        ],
    )
    def test_get_year(self, utils: DateTimeUtils, year: str, expected: Optional[int]):
        assert utils.get_year(year) == expected

    @pytest.mark.parametrize(
        "month, expected",
        [
            ("1", 1),
            ("01", 1),
            ("12", 12),
            ("Jan", 1),
            ("Marc", 3),
            ("Ma", None),
            ("001", None),
            ("13", None),
        ],
    )
    def test_get_month(self, utils: DateTimeUtils, month: str, expected: Optional[int]):
        assert utils.get_month(month) == expected

    @pytest.mark.parametrize(
        "day, expected",
        [("1", 1), ("01", 1), ("031", None), ("32", None), ("31", 31)],
    )
    def test_get_day(self, utils: DateTimeUtils, day: str, expected: Optional[int]):
        assert utils.get_day(day) == expected
