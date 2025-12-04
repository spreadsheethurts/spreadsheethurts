import builtins
from datetime import datetime
from typing import Optional, Unpack

from .utils import DateTimeUtils
from wizard.feature import WeirdFeature
from wizard.utils import classic_round
from wizard.typ import ExcelDateTime

from ...common.pattern import Primitive
from .base import ExcelDateTimeAlikeBase, TimeDict

SPACE = Primitive.space()
COLON = Primitive.colon()
DOT = Primitive.dot()
DASH = Primitive.hyphen()
SLASH = Primitive.slash()
ANYSPACE = Primitive.anyspace()
SOMESPACE = Primitive.somespace()


NAMED_HOUR = Primitive.digits().named("hour")
NAMED_MINUTE = Primitive.digits().named("minute")
NAMED_SECOND = Primitive.digits().named("second")
NAMED_MICROSECOND = Primitive.digits().named("microsecond")
NAMED_APM = Primitive.apm().named("apm")
SOMESPACE_APM = (SOMESPACE + NAMED_APM).group()


util = DateTimeUtils()


def validate_time_ranges(
    nums: list[int],
    bases: list[int],
    maxs: list[int | float],
) -> bool:
    """Verify if the list of numbers adheres to a set of constraints.

    This function recursively checks the validity of each number in the `nums` list against
    corresponding base and max values in the `bases` and `maxs` lists.

    Conditions:
    1. If the first value (head) in `nums` is less than its corresponding base, the function
        recursively checks the remaining numbers.
    2. If the head value falls within the range [base, max], the function ensures that all remaining
        numbers in `nums` are less than their corresponding base values.
    3. Otherwise, the function returns `False`.
    """

    assert len(nums) == len(bases) == len(maxs), "Lengths of lists must be equal."

    if len(nums) == 0:
        return True

    head, *rests = nums
    head_base, *base_rests = bases
    head_max, *max_rests = maxs

    if head < head_base:
        return validate_time_ranges(rests, base_rests, max_rests)
    elif head_base <= head <= head_max:
        return all(map(lambda zipped: zipped[0] < zipped[1], zip(rests, base_rests)))
    else:
        return False


class TimeAlike(ExcelDateTimeAlikeBase):
    @classmethod
    def is_datetime_valid(
        cls,
        check_second: bool = True,
        **kwargs: TimeDict,
    ) -> Optional[ExcelDateTime]:
        """Verify if the time is valid."""
        hour, minute, second, microsecond, apm = (
            kwargs.get("hour", 0),
            kwargs.get("minute", 0),
            kwargs.get("second", 0),
            kwargs.get("microsecond", 0),
            kwargs.get("apm", None),
        )

        # convert the digits into integers
        hour, minute, microsecond = (
            util.get_hour(hour),
            util.get_minute(minute),
            util.get_microsecond(microsecond),
        )

        second = util.get_second(second) if check_second else int(second)

        # if any of the values is None, return false
        if builtins.any(item is None for item in (hour, minute, second, microsecond)):
            return None

        # If the apm is not None, the hour, minute, and second must be within the range [0, 12], [0, 59], and [0, 59]
        if apm:
            if not (0 <= hour <= 12 and 0 <= minute <= 59 and 0 <= second <= 59):
                return None
            hour = cls.convert_12hr_to_24hr(hour, apm)
        else:
            max_second = util.max_second if check_second else float("inf")
            if not validate_time_ranges(
                [hour, minute, second],
                [24, 60, 60],
                [util.max_hour, util.max_minute, max_second],
            ):
                return None

        try:
            return ExcelDateTime.with_overflow_times(
                hour=hour, minute=minute, second=second, microsecond=microsecond
            )
        # If an exception occurs (e.g., the execution time exceeds the maximum limit), return `None`.
        except Exception:
            return None


class Hour(TimeAlike):
    EXAMPLES = ["12:", "888:", "00:", "0888:", "12 am"]
    # Note: apm is invalid when colon is present
    PATTERN = (
        (NAMED_HOUR + COLON).join_both_ends(ANYSPACE)
        | (NAMED_HOUR + SOMESPACE_APM + ANYSPACE).clone()
    ).compile()


class HourMinute(TimeAlike):
    HOUR_MINUTE = (NAMED_HOUR + COLON + NAMED_MINUTE).join(ANYSPACE).group()

    PATTERN = (HOUR_MINUTE + SOMESPACE_APM.maybe() + ANYSPACE).compile()

    EXAMPLES = [
        "12:34",
        "888:34",
        "12:888",
        "12:33 am",
        "0888:34",
        "12:0134",
    ]


class HourMinuteSpecial(TimeAlike):
    EXAMPLES = [
        "12:34.",
        "888:34 .",
        "12:34:",
        "888:34:",
        "12:34 -",
        "888:34 -  ",
        "12:34/",
        "888:34 /",
    ]

    PATTERN = (
        # Note: Only trailing spaces are allowed, leading spaces are invalid
        (HourMinute.HOUR_MINUTE + (DOT | COLON | DASH | SLASH))
        .join_with_tail(ANYSPACE)
        .compile()
    )


class MinuteSecondMicrosecond(TimeAlike):

    # Note: Spaces are allowed around DOT
    MINUTE_SECOND = (
        (NAMED_MINUTE + COLON + NAMED_SECOND + DOT + NAMED_MICROSECOND)
        .join(ANYSPACE)
        .group()
    )

    PATTERN = (MINUTE_SECOND + SOMESPACE_APM.maybe() + ANYSPACE).compile()

    EXAMPLES = [
        "34:56.11",
        "888:56.22",
        "34:888.33",
        "34:55.33 am",
    ]


class MinuteSecondMicrosecondSpecial(TimeAlike):

    PATTERN = (
        # Note: Only trailing spaces are allowed, leading spaces are invalid
        (MinuteSecondMicrosecond.MINUTE_SECOND + (COLON | DASH | SLASH))
        .join_with_tail(ANYSPACE)
        .compile()
    )

    EXAMPLES = [
        "34:56.11:",
        "888:56.22:",
        "34:888.33:",
        "34:56.11 -",
        "888:56.22- ",
        "34:888.33-",
        "34:56.11 /",
        "888:56.22/ ",
        "34:888.33/",
    ]


class HourMinuteSecond(TimeAlike):
    EXAMPLES = [
        "12:34:56",
        "888:34:56",
        "12:888:56",
        "12:34:888",
        "10:34:33 am",
    ]

    HOUR_MINUTE_SECOND = (
        (NAMED_HOUR + COLON + NAMED_MINUTE + COLON + NAMED_SECOND)
        .join(ANYSPACE)
        .group()
    )

    PATTERN = (HOUR_MINUTE_SECOND + SOMESPACE_APM.maybe() + ANYSPACE).compile()


class HourMinuteSecondSpecial(TimeAlike):
    EXAMPLES = [
        "12:34:56. ",
        "888:34:56 .",
        "12:34:56:",
        "888:34:56 :",
        "12:34:56-   ",
        "888:34:56-",
        "12:34:56/",
        "888:34:56/",
    ]
    PATTERN = (
        # Note: Only trailing spaces are allowed, leading spaces are invalid
        (HourMinuteSecond.HOUR_MINUTE_SECOND + (DOT | COLON | DASH | SLASH))
        .join_with_tail(ANYSPACE)
        .compile()
    )


class HourMinuteSecondMicrosecond(TimeAlike):
    EXAMPLES = [
        "12:34:56.11",
        "888:34:56.22",
        "12:888:56.33",
        "12:34:888.44",
        "12:34:33.55 am",
        "12:11:33.55 pM",
    ]

    HOUR_MINUTE_SECOND_MICROSECOND = (
        (HourMinuteSecond.HOUR_MINUTE_SECOND + DOT + NAMED_MICROSECOND)
        .join(ANYSPACE)
        .group()
    )

    PATTERN = (
        HOUR_MINUTE_SECOND_MICROSECOND + SOMESPACE_APM.maybe() + ANYSPACE
    ).compile()


class HourMinuteSecondMicrosecondSpecial(TimeAlike):
    EXAMPLES = [
        "12:34:56.11:",
        "888:34:56.22:",
        "12:34:56.11-",
        "888:34:56.22-",
        "12:34:56.11/",
        "888:34:56.22/",
    ]
    PATTERN = (
        # Note: Only trailing spaces are allowed, leading spaces are invalid
        (
            HourMinuteSecondMicrosecond.HOUR_MINUTE_SECOND_MICROSECOND
            + (COLON | DASH | SLASH)
        )
        .join_with_tail(ANYSPACE)
        .compile()
    )


# Since all leaf classes will be regarded as features, we need to introduce one more abstract class
class WeirdHourDecimalMinuteBase(TimeAlike, WeirdFeature):
    """Matches a pattern consisting of an hour, a decimal minute, and additional parts, where the decimal portion represents both seconds and milliseconds."""

    TYPE = "Weird"
    HOUR_DECIMAL_MINUTE = (
        (NAMED_HOUR + COLON + NAMED_MINUTE + DOT + NAMED_SECOND + COLON)
        .join(ANYSPACE)
        .group()
    )

    @classmethod
    def add_weird_milliseconds(cls, groupdict: TimeDict) -> TimeDict:
        """Add weird milliseconds to the groupdict."""
        sec = groupdict.get("second")
        digit = "." + str(sec)
        mill = classic_round(float(digit) * 1e3)
        # Converts the millisecond to microsecond
        groupdict["microsecond"] = int(mill * 1e3)
        return groupdict

    @classmethod
    def fullmatch(cls, content: str) -> Optional[TimeDict]:
        if groupdict := super().fullmatch(content):
            return cls.add_weird_milliseconds(groupdict)
        return None

    @classmethod
    def match(cls, content: str) -> tuple[Optional[TimeDict], str]:
        (groupdict, end) = super().match(content)
        if groupdict:
            return cls.add_weird_milliseconds(groupdict), end
        return None, 0

    @classmethod
    def is_datetime_valid(cls, **kwargs: Unpack[TimeDict]) -> Optional[datetime]:
        return super().is_datetime_valid(
            **kwargs,
            check_second=False,
        )


class WeirdHourDecimalMinuteIntegerBase(WeirdHourDecimalMinuteBase):
    # Trick: We temporarily add DIGIT_NAME to the groupdict for validation purposes,
    # even though it's not part of the TimeDict type definition.
    DIGIT_NAME = "digit"
    HOUR_DECIMAL_MINUTE_SECOND = (
        (
            WeirdHourDecimalMinuteBase.HOUR_DECIMAL_MINUTE
            + Primitive.digits().named(DIGIT_NAME)
        )
        .join(ANYSPACE)
        .group()
    )

    @classmethod
    def validate(cls, groupdict: TimeDict) -> Optional[TimeDict]:
        digit = groupdict.pop(cls.DIGIT_NAME)
        if util.is_second_valid(digit):
            return groupdict
        return None


class WeirdHourDecimalMinuteInteger(WeirdHourDecimalMinuteIntegerBase):
    EXAMPLES = [
        "12:34.56:11",
        "888:34.56:11",
        "12:888.56:11",
        "12:34.99999:11",
        "10:34.33:1 am",
        "10:34.33:1 pm",
    ]

    PATTERN = (
        WeirdHourDecimalMinuteIntegerBase.HOUR_DECIMAL_MINUTE_SECOND
        + SOMESPACE_APM.maybe()
        + ANYSPACE
    ).compile()


class WeirdHourDecimalMinuteSecondSpecial(WeirdHourDecimalMinuteIntegerBase):
    EXAMPLES = ["12:34.56:11.", "888:34.56:11-", "12:888.56:11/", "12:34.888:11:"]

    PATTERN = (
        (
            WeirdHourDecimalMinuteIntegerBase.HOUR_DECIMAL_MINUTE_SECOND
            + (DOT | DASH | SLASH | COLON)
        )
        .join_with_tail(ANYSPACE)
        .compile()
    )


class WeirdHourDecimalMinuteMonthNameBase(WeirdHourDecimalMinuteBase):
    # Trick: We temporarily add MONTH_NAME to the groupdict for validation purposes,
    # even though it's not part of the TimeDict type definition.
    MONTH_NAME = "month"
    HOUR_DECIMAL_MINUTE_MONTH_NAME = (
        (
            WeirdHourDecimalMinuteBase.HOUR_DECIMAL_MINUTE
            + Primitive.letters().named(MONTH_NAME)
        )
        .join(ANYSPACE)
        .group()
    )

    @classmethod
    def validate(cls, groupdict: TimeDict) -> Optional[TimeDict]:
        month = groupdict.pop(cls.MONTH_NAME)
        if util.get_month(month):
            return groupdict
        return None


class WeirdHourDecimalMinuteMonthName(WeirdHourDecimalMinuteMonthNameBase):
    EXAMPLES = [
        "12:34.56:jan",
        "888:34.56:jan",
        "12:888.56:jan",
        "12:34.99999:jan",
        "10:34.33:jan am",
        "10:34.33:jan pm",
    ]

    PATTERN = (
        WeirdHourDecimalMinuteMonthNameBase.HOUR_DECIMAL_MINUTE_MONTH_NAME
        + SOMESPACE_APM.maybe()
        + ANYSPACE
    ).compile()


class WeirdHourDecimalMinuteMonthNameSpecial(WeirdHourDecimalMinuteMonthNameBase):
    EXAMPLES = ["12:34.56:jan.", "888:34.56:jan-", "12:888.56:jan/", "12:34.888:jan:"]

    PATTERN = (
        (
            WeirdHourDecimalMinuteMonthNameBase.HOUR_DECIMAL_MINUTE_MONTH_NAME
            + (DOT | DASH | SLASH | COLON)
        )
        .join_with_tail(ANYSPACE)
        .compile()
    )
