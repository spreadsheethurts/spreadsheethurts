import pytest
from datetime import timedelta

from wizard.typ import GregorianDateTime
from wizard.features.calc.datetime_alike.base import CalcDateTimeAlikeBase


class TestGregorianDateTime:

    @pytest.fixture(scope="class")
    def year_month_day_ordinal(self) -> tuple[int, int, int, int]:
        return [  # julian dates
            (100, 2, 29, 36219),
            (200, 2, 28, 72743),
            (1582, 10, 4, 577737),
            # gregorian dates
            (1582, 10, 15, 577738),
            (2020, 1, 1, 737427),
        ]

    @pytest.mark.parametrize(
        "year, month, day",
        [(1582, 10, day) for day in range(5, 15)],
    )
    def test_invalid_dates(self, year, month, day):
        with pytest.raises((ValueError, OverflowError)):
            GregorianDateTime(year, month, day)

    def test_toordinal(self, year_month_day_ordinal):
        for year, month, day, ordinal in year_month_day_ordinal:
            assert GregorianDateTime(year, month, day).toordinal() == ordinal

    def test_fromordinal(self, year_month_day_ordinal):
        for year, month, day, ordinal in year_month_day_ordinal:
            assert GregorianDateTime.fromordinal(ordinal) == GregorianDateTime(
                year, month, day
            )

    @pytest.mark.parametrize(
        "dt, delta, expected",
        [
            (
                GregorianDateTime(1582, 10, 15, 12, 0, 0),
                timedelta(days=1, seconds=1),
                GregorianDateTime(1582, 10, 16, 12, 0, 1),
            ),
            (
                GregorianDateTime(
                    1582,
                    10,
                    4,
                ),
                timedelta(days=1, hours=-1),
                GregorianDateTime(1582, 10, 4, 23, 0, 0),
            ),
        ],
    )
    def test_add(self, dt, delta, expected):
        assert dt + delta == expected

    @pytest.mark.parametrize(
        "dt1, dt2, expected",
        [
            (GregorianDateTime(1582, 10, 15), GregorianDateTime(1582, 10, 4), 1),
            (
                GregorianDateTime(1582, 10, 4) + timedelta(days=1),
                timedelta(days=1),
                GregorianDateTime(1582, 10, 4),
            ),
        ],
    )
    def test_sub(self, dt1, dt2, expected):
        sub = dt1 - dt2
        if isinstance(sub, timedelta):
            assert CalcDateTimeAlikeBase.to_scalar_number(sub) == expected
        else:
            assert sub == expected

    @pytest.mark.parametrize(
        "dt1, dt2",
        [
            (GregorianDateTime(100, 2, 28), GregorianDateTime(100, 2, 29)),
            (GregorianDateTime(1582, 10, 4), GregorianDateTime(1582, 10, 15)),
            (GregorianDateTime(1, 1, 1), GregorianDateTime(1582, 10, 4)),
        ],
    )
    def test_less_than(self, dt1, dt2):
        assert (dt1 < dt2) is True

    @pytest.mark.parametrize(
        "dt, format, expected",
        [
            (GregorianDateTime(100, 2, 28), "%Y-%m-%d", "0100-02-28"),
            (GregorianDateTime(100, 2, 29), "%Y-%m-%d", "0100-02-29"),
            (GregorianDateTime(1582, 10, 15), "%Y-%m-%d", "1582-10-15"),
        ],
    )
    def test_strftime(self, dt: GregorianDateTime, format: str, expected: str):
        assert dt.strftime(format) == expected

    @pytest.mark.parametrize(
        "date_string, format, expected",
        [
            ("0100-02-28", "%Y-%m-%d", GregorianDateTime(100, 2, 28)),
            ("0100-02-29", "%Y-%m-%d", GregorianDateTime(100, 2, 29)),
            ("32767-10-15", "%Y-%m-%d", GregorianDateTime(32767, 10, 15)),
        ],
    )
    def test_strptime(self, date_string: str, format: str, expected: GregorianDateTime):
        assert GregorianDateTime.strptime(date_string, format) == expected
