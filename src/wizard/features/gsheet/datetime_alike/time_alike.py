from typing import Optional

from wizard.features.common.datetime_alike.datetime import DatetimeDict
from wizard.features.gsheet.num_alike import SOMESPACE
from .base import GsheetDateTimeAlikeBase, TimeDict
from ...common.pattern import Primitive
from wizard.typ import GsheetDateTime
from .utils import DateTimeUtils


NEGATIVE_SIGN = Primitive.minus()
NAMED_HOUR = Primitive.digits().named("hour")
NAMED_MINUTE = Primitive.digits().named("minute")
NAMED_SECOND = Primitive.digits().named("second")
NAMED_MICROSECOND = Primitive.digits().named("microsecond")
NAMED_APM = Primitive.apm().named("apm")

# fmt: off
MAYBE_NEGATIVE_NAMED_HOUR = (NEGATIVE_SIGN.maybe() + Primitive.digits()).named("hour")
MAYBE_NEGATIVE_NAMED_MINUTE = (NEGATIVE_SIGN.maybe() + Primitive.digits()).named("minute")
MAYBE_NEGATIVE_NAMED_SECOND = (NEGATIVE_SIGN.maybe() + Primitive.digits()).named("second")
# fmt: on

COLON = Primitive.colon()
DOT = Primitive.dot()
COLONANYSPACE = (COLON + Primitive.anyspace()).group()
ANYSPACE = Primitive.anyspace()

utils = DateTimeUtils()


class TimeAlike(GsheetDateTimeAlikeBase):
    @classmethod
    def is_datetime_valid(cls, **kwargs: TimeDict) -> Optional[GsheetDateTime]:
        # The hour, minute, and second could be negative
        max = GsheetDateTime(99999, 12, 31, 23, 59, 59, 999999)
        hour, minute, second, microsecond, apm = (
            kwargs.get("hour", 0),
            kwargs.get("minute", 0),
            kwargs.get("second", 0),
            kwargs.get("microsecond", 0),
            kwargs.get("apm", None),
        )
        # convert the digits into integers
        hour, minute, second, microsecond = (
            utils.get_hour(hour),
            utils.get_minute(minute),
            utils.get_second(second),
            utils.get_microsecond(microsecond),
        )

        if apm:
            # when apm is present, hour must be less than 12
            if hour > 12:
                return None

            hour = cls.convert_12hr_to_24hr(hour, apm)

        if any(item is None for item in (hour, minute, second, microsecond)):
            return None
        try:
            dt = GsheetDateTime.with_overflow_times(
                year=1899,
                month=12,
                day=30,
                hour=hour,
                minute=minute,
                second=second,
                microsecond=microsecond,
            )
            if dt > max:
                return None
            return dt
        except Exception:
            return None


class Hour(TimeAlike):
    EXAMPLES = ["12 am", "1 pm"]
    COUNTER_EXAMPLES = ["13 pm"]
    PATTERN = (NAMED_HOUR + NAMED_APM).join_both_ends(ANYSPACE).compile()


class HourMinute(TimeAlike):
    EXAMPLES = [
        "9: 01",
        "0888:111",
        "12:123",
        "12:1 am",
        "12:11111am",
        "1:11111 am",
        "12:1. am",
    ]
    COUNTER_EXAMPLES = ["12:1", "12 :01", "9999999999:01"]

    BACKBONE = (NAMED_HOUR + COLONANYSPACE + MAYBE_NEGATIVE_NAMED_MINUTE).group()
    PATTERN = (
        # space is not allowed between hour and colon
        (
            BACKBONE.surround_anyspace()
            | (
                BACKBONE.clone()
                + ANYSPACE
                # somespace is required between dot and apm
                + (DOT + SOMESPACE).maybe()
                + NAMED_APM
            ).surround_anyspace()
        ).compile()
    )

    @classmethod
    def validate(cls, groupdict: DatetimeDict) -> DatetimeDict | None:
        # The minute must be at least two digits when apm is absent
        minute = groupdict["minute"]
        if len(minute) < 2 and not groupdict.get("apm"):
            return None
        return groupdict


class HourMinuteSecond(TimeAlike):
    EXAMPLES = ["12:34: 56", "12:99999:56 am", "12:999: 111 pm", "0:1:1. am"]

    BACKBONE = (
        NAMED_HOUR
        + COLONANYSPACE
        + MAYBE_NEGATIVE_NAMED_MINUTE
        + COLONANYSPACE
        + MAYBE_NEGATIVE_NAMED_SECOND
    ).group()
    PATTERN = (
        BACKBONE.surround_anyspace()
        | (
            BACKBONE.clone() + ANYSPACE + (DOT + SOMESPACE).maybe() + NAMED_APM
        ).surround_anyspace()
    ).compile()


class HourMinuteSecondMicrosecond(TimeAlike):
    EXAMPLES = ["12:888:5777.789", "12: 34: 56.789 am", "1224: 9988:886655.999999"]

    BACKBONE = (
        NAMED_HOUR
        + COLONANYSPACE
        + MAYBE_NEGATIVE_NAMED_MINUTE
        + COLONANYSPACE
        + MAYBE_NEGATIVE_NAMED_SECOND
        # No spaces around the dot
        + DOT
        + NAMED_MICROSECOND
    ).group()
    PATTERN = (
        BACKBONE.surround_anyspace()
        | (
            BACKBONE.clone() + ANYSPACE + (DOT + SOMESPACE).maybe() + NAMED_APM
        ).surround_anyspace()
    ).compile()
