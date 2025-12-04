import pytest

from wizard.features.calc.datetime_alike.time_alike import TimeAlike, GregorianDateTime


class TestTimeAlike:
    # fmt: off
    @pytest.mark.parametrize(
        "hour, minute, second, apm, expected",
        [
            (0, 2161, 1, "pm", GregorianDateTime.with_overflow_times(1899, 12, 30, 48, 1, 1, 0)),
            (0, 2161, 1, "am", GregorianDateTime.with_overflow_times(1899, 12, 30, 36, 1, 1, 0)),
            (12, 0, 0, "am", GregorianDateTime.with_overflow_times(1899, 12, 30, 0, 0, 0, 0)),
            (0, 0, 0, "pm", GregorianDateTime.with_overflow_times(1899, 12, 30, 12, 0, 0, 0)),
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
