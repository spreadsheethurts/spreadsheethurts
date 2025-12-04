import pytest
from typing import Optional

from wizard.features.gsheet.datetime_alike.utils import DateTimeUtils


class TestDateTimeUtils:
    @pytest.fixture
    def utils(self):
        return DateTimeUtils()

    @pytest.mark.parametrize(
        "year, expected",
        [
            ("0", 2000),
            ("00", 2000),
            ("000", 2000),
            ("00000001", 2001),
            ("30", 1930),
            ("100", 100),
            ("99999", 99999),
            ("100000", None),
        ],
    )
    def test_get_year(self, utils: DateTimeUtils, year: str, expected: Optional[int]):
        assert utils.get_year(year) == expected
