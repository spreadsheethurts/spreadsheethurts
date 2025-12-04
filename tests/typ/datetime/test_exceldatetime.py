import pytest
from datetime import datetime, timedelta

from wizard.typ import ExcelDateTime


class TestExcelDateTime:

    @pytest.mark.parametrize(
        "year, month, day, expected",
        [
            (1900, 2, 28, datetime(1900, 2, 28).toordinal()),
            (1900, 2, 29, datetime(1900, 2, 28).toordinal() + 1),
            (1900, 3, 1, datetime(1900, 3, 1).toordinal() + 1),
            (1900, 1, 1, datetime(1900, 1, 1).toordinal()),
        ],
    )
    def test_toordinal(self, year, month, day, expected):
        assert ExcelDateTime(year, month, day).toordinal() == expected

    @pytest.mark.parametrize(
        "year, month, day",
        [
            (1900, 2, 28),
            (1900, 2, 29),
            (1900, 3, 1),
            (1900, 1, 1),
        ],
    )
    def test_fromordinal(self, year, month, day):
        assert ExcelDateTime.fromordinal(
            ExcelDateTime(year, month, day).toordinal()
        ) == ExcelDateTime(year, month, day)

    @pytest.mark.parametrize(
        "dt, delta, expected",
        [
            (ExcelDateTime(1900, 2, 28), timedelta(days=1), ExcelDateTime(1900, 2, 29)),
            (ExcelDateTime(1900, 2, 29), timedelta(days=1), ExcelDateTime(1900, 3, 1)),
            (ExcelDateTime(1900, 3, 1), timedelta(days=1), ExcelDateTime(1900, 3, 2)),
        ],
    )
    def test_add(self, dt, delta, expected):
        assert dt + delta == expected

    @pytest.mark.parametrize(
        "dt, format, expected",
        [
            (ExcelDateTime(1900, 2, 28), "%Y-%m-%d", "1900-02-28"),
            (ExcelDateTime(1900, 2, 29), "%Y-%m-%d", "1900-02-29"),
            (ExcelDateTime(1900, 3, 1), "%Y-%m-%d", "1900-03-01"),
        ],
    )
    def test_strftime(self, dt, format, expected):
        assert dt.strftime(format) == expected

    @pytest.mark.parametrize(
        "date_string, format, expected",
        [
            ("1900-02-28", "%Y-%m-%d", ExcelDateTime(1900, 2, 28)),
            ("1900-02-29", "%Y-%m-%d", ExcelDateTime(1900, 2, 29)),
            ("1900-03-01", "%Y-%m-%d", ExcelDateTime(1900, 3, 1)),
        ],
    )
    def test_strptime(self, date_string, format, expected):
        assert ExcelDateTime.strptime(date_string, format) == expected
