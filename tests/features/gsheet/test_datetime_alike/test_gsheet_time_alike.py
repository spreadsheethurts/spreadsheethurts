import pytest

from wizard.features.gsheet.datetime_alike.time_alike import TimeAlike, GsheetDateTime


class TestTimeAlike:
    # fmt: off
    @pytest.mark.parametrize(
        "hour, minute, second,  apm, expected",
        [
            (0, 999, 0, None, GsheetDateTime.with_overflow_times(1899, 12, 30, 16, 39, 0, 0)),
            (0, 999, 0, "am", GsheetDateTime.with_overflow_times(1899, 12, 30, 16, 39, 0, 0)),
            (0, 999, 0, "pm", GsheetDateTime.with_overflow_times(1899, 12, 30, 28, 39, 0, 0)),
            (12, 999, 0, None, GsheetDateTime.with_overflow_times(1899, 12, 30, 28, 39, 0, 0)),
            (12, 999, 0, "am", GsheetDateTime.with_overflow_times(1899, 12, 30, 16, 39, 0, 0)),
            (12, 999, 0, "pm", GsheetDateTime.with_overflow_times(1899, 12, 30, 28, 39, 0, 0)),
            (10, 9999, 0, None, GsheetDateTime.with_overflow_times(1899, 12, 30, 176, 39, 0, 0)),
            (10, 9999, 0, "am", GsheetDateTime.with_overflow_times(1899, 12, 30, 176, 39, 0, 0)),
            (10, 9999, 0, "pm", GsheetDateTime.with_overflow_times(1899, 12, 30, 188, 39, 0, 0)),
        ],
    )
    # fmt: on
    def test_is_datetime_valid(self, hour, minute, second, apm, expected):
        assert (
            TimeAlike.is_datetime_valid(
                hour=hour, minute=minute, second=second, microsecond=0, apm=apm
            )
            == expected
        )
