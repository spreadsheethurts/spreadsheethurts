import pytest
from datetime import timedelta

from wizard.typ import GsheetDateTime
from wizard.features.gsheet.datetime_alike.base import GsheetDateTimeAlikeBase


class TestGsheetDateTimeAlikeBase:

    @pytest.mark.parametrize(
        "delta, expected",
        [
            (timedelta(days=1), 1),
            (timedelta(days=32, hours=1, minutes=20, seconds=30), 32.055902777777774),
        ],
    )
    def test_to_scalar_number_delta(self, delta, expected):
        assert GsheetDateTimeAlikeBase.to_scalar_number(delta) == expected

    @pytest.mark.parametrize(
        "dt, expected",
        [
            (GsheetDateTime(1899, 12, 31), 1),
            (GsheetDateTime(1900, 1, 1), 2),
            (GsheetDateTime(1900, 3, 1), 61),
            (GsheetDateTime(100, 1, 1), -657434),
            (GsheetDateTime(99999, 1, 1), 35829926),
        ],
    )
    def test_to_scalar_number_dt(self, dt, expected):
        assert GsheetDateTimeAlikeBase.to_scalar_number(dt) == expected

    @pytest.mark.parametrize(
        "number, expected",
        [
            (1, GsheetDateTime(1899, 12, 31)),
            (2, GsheetDateTime(1900, 1, 1)),
            (61, GsheetDateTime(1900, 3, 1)),
            (-657434, GsheetDateTime(100, 1, 1)),
            (35829926, GsheetDateTime(99999, 1, 1)),
        ],
    )
    def test_to_datetime(self, number, expected):
        assert GsheetDateTimeAlikeBase.to_datetime(number) == expected
