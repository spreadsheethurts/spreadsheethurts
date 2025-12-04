import pytest

from wizard.typ import GsheetDateTime


class TestGsheetDateTime:

    @pytest.fixture(scope="class")
    def year_month_day_ordinal(self) -> list[tuple[int, int, int, int]]:
        return [
            (100, 1, 1, 36160),
            (2000, 1, 1, 730120),
            (9999, 1, 1, 3651695),
            (99999, 1, 1, 36523520),
            (32767, 1, 1, 11967536),
        ]

    @pytest.fixture(scope="class")
    def dt_format_strftime(self) -> list[tuple[GsheetDateTime, str, str]]:
        return [
            (GsheetDateTime(100, 1, 1), "%Y-%m-%d", "0100-01-01"),
            (GsheetDateTime(2000, 1, 1), "%Y-%m-%d", "2000-01-01"),
            (GsheetDateTime(9999, 1, 1), "%Y-%m-%d", "9999-01-01"),
            (GsheetDateTime(99999, 1, 1), "%Y-%m-%d", "99999-01-01"),
            (GsheetDateTime(32767, 1, 1), "%Y-%m-%d", "32767-01-01"),
        ]

    def test_toordinal(self, year_month_day_ordinal):
        for year, month, day, expected in year_month_day_ordinal:
            assert GsheetDateTime(year, month, day).toordinal() == expected

    def test_fromordinal(self, year_month_day_ordinal):
        for year, month, day, expected in year_month_day_ordinal:
            assert GsheetDateTime.fromordinal(expected) == GsheetDateTime(
                year, month, day
            )

    def test_strftime(self, dt_format_strftime):
        for dt, format, expected in dt_format_strftime:
            assert dt.strftime(format) == expected

    def test_strptime(self, dt_format_strftime):
        for dt, format, expected in dt_format_strftime:
            assert GsheetDateTime.strptime(expected, format) == dt
