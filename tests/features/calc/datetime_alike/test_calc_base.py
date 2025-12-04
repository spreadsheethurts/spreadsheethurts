import pytest
from datetime import timedelta

from wizard.features.calc.datetime_alike.base import CalcDateTimeAlikeBase
from wizard.typ import GregorianDateTime


class TestCalcDateTimeAlikeBase:

    @pytest.mark.parametrize(
        "delta, expected",
        [
            (timedelta(days=1), 1),
            (timedelta(days=32, hours=1, minutes=20, seconds=30), 32.055902777777774),
        ],
    )
    def test_to_scalar_number_delta(self, delta, expected):
        assert CalcDateTimeAlikeBase.to_scalar_number(delta) == expected

    @pytest.mark.parametrize(
        "dt, expected",
        [
            (GregorianDateTime(1899, 12, 31), 1),
            (GregorianDateTime(1900, 1, 1), 2),
            (GregorianDateTime(2000, 12, 13), 36873),
            (GregorianDateTime(1582, 10, 4), -115859),
            (GregorianDateTime(100, 2, 29), -657377),
            (GregorianDateTime(1, 6, 1), -693444),
        ],
    )
    def test_to_scalar_number_dt(self, dt, expected):
        assert CalcDateTimeAlikeBase.to_scalar_number(dt) == expected

    @pytest.mark.parametrize(
        "number, expected",
        [
            (1, GregorianDateTime(1899, 12, 31)),
            (2, GregorianDateTime(1900, 1, 1)),
            (36873, GregorianDateTime(2000, 12, 13)),
            (-115859, GregorianDateTime(1582, 10, 4)),
            (-657377, GregorianDateTime(100, 2, 29)),
            (-693444, GregorianDateTime(1, 6, 1)),
        ],
    )
    def test_to_datetime(self, number, expected):
        assert CalcDateTimeAlikeBase.to_datetime(number) == expected
