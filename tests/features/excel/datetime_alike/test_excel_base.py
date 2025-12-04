import pytest
from wizard.features.excel.datetime_alike.base import ExcelDateTimeAlikeBase
from wizard.typ import ExcelDateTime


class TestExcelDateTimeAlikeBase:

    @pytest.mark.parametrize(
        "dt, expected",
        [
            (ExcelDateTime(1900, 1, 0), 693595),
            (ExcelDateTime(1900, 1, 1), 693596),
            (ExcelDateTime(1900, 3, 1), 693656),
        ],
    )
    def test_toordinal(self, dt, expected):
        assert dt.toordinal() == expected

    @pytest.mark.parametrize(
        "dt, expected",
        [
            (ExcelDateTime(1900, 1, 1), 1),
            (ExcelDateTime(1900, 3, 1), 61),
            (ExcelDateTime(1900, 12, 31), 366),
        ],
    )
    def test_to_scalar_number_dt(self, dt, expected):
        assert ExcelDateTimeAlikeBase.to_scalar_number(dt) == expected

    @pytest.mark.parametrize(
        "number, expected",
        [
            (1, ExcelDateTime(1900, 1, 1)),
            (61, ExcelDateTime(1900, 3, 1)),
            (366, ExcelDateTime(1900, 12, 31)),
        ],
    )
    def test_to_datetime(self, number, expected):
        assert ExcelDateTimeAlikeBase.to_datetime(number) == expected
