from typing import Optional, Literal

from wizard.feature import WeirdFeature
from wizard.typ import GregorianDateTime

from .utils import DateTimeUtils
from .base import CalcDateTimeAlikeBase, TimeDict
from ...common.pattern import Primitive, Placeholder


NAMED_HOUR = Primitive.digits().named("hour")
NAMED_MINUTE = Primitive.digits().named("minute")
NAMED_SECOND = Primitive.digits().named("second")
NAMED_MICROSECOND = Primitive.digits().named("microsecond")
NAMED_APM = Primitive.apm().named("apm")

COMMA = Primitive.comma()
COLON = Primitive.colon()
DOT = Primitive.dot()
NAMED_SIGN = (Primitive.minus() | Primitive.plus()).named("sign")

ANYSPACE = Primitive.anyspace()
SOMESPACE = Primitive.somespace()


util = DateTimeUtils()


def validate_time_ranges(hour: int, minute: int, second: int) -> bool:
    """Verify if the list of numbers adheres the following rules.

    1. When hour and minute are both 0, seconds can be any positive integer
    2. When hour is 0 but minute is non-zero:
       - seconds must be less than 60
       - minute can be any positive integer
    3. When hour is non-zero:
       - both minute and seconds must be less than 60
    """

    if hour == 0 and minute == 0:
        return second <= 2**31 - 1
    elif hour == 0 and minute != 0:
        return minute < 2**31 - 1 and second < 60
    else:
        return minute < 60 and second < 60


class TimeAlike(CalcDateTimeAlikeBase):

    @classmethod
    def is_datetime_valid(
        cls,
        sign: Optional[Literal["+", "-"]] = None,
        datetime: bool = False,
        **kwargs: TimeDict,
    ) -> Optional[GregorianDateTime]:
        """Verify if the time is valid."""
        hour, minute, second, microsecond, apm = (
            kwargs.get("hour", 0),
            kwargs.get("minute", 0),
            kwargs.get("second", 0),
            kwargs.get("microsecond", 0),
            kwargs.get("apm", None),
        )

        # convert the digits into integers
        hour, minute, second, microsecond = (
            util.get_hour(hour),
            util.get_minute(minute),
            util.get_second(second),
            util.get_microsecond(microsecond),
        )

        # if any of the values is None, return false
        if any(item is None for item in (hour, minute, second, microsecond)):
            return None

        if not validate_time_ranges(hour, minute, second):
            return None

        # When apm is used: hour must be < 12
        if apm:
            if hour > 12:
                return None
            # Curiously, when AM/PM is specified for time only, the minute can exceed 59.
            # However, for datetime, the minute must be less than 60.
            if datetime and hour == 0 and minute > 59:
                return None
            hour = cls.convert_12hr_to_24hr(hour, apm)

        try:
            if sign == "-":
                hour = -hour
                minute = -minute
                second = -second
                microsecond = -microsecond
            return GregorianDateTime.with_overflow_times(
                year=1899,
                month=12,
                day=30,
                hour=hour,
                minute=minute,
                second=second,
                microsecond=microsecond,
            )
        # if an exception occurs (e.g., the datetime value is invalid), return `None`.
        except Exception:
            return None


class Hour(TimeAlike):
    EXAMPLES = ["12 : ", "9: pm", "0888: ", "12 am"]

    PATTERN = (
        (NAMED_HOUR + COLON + NAMED_APM.maybe()).join_both_ends(ANYSPACE)
        | (NAMED_HOUR + NAMED_APM).join_both_ends(ANYSPACE).clone()
    ).compile()


class HourWeird(TimeAlike, WeirdFeature):
    EXAMPLES = ["12. am", "9. pm"]
    PATTERN = (
        ((NAMED_HOUR + DOT).group() + NAMED_APM).join_both_ends(ANYSPACE).compile()
    )


class HourSpecial(TimeAlike):
    EXAMPLES = ["11-: pm", "111-:"]

    PATTERN = (
        (NAMED_HOUR + NAMED_SIGN + COLON + NAMED_APM.maybe())
        .join_both_ends(ANYSPACE)
        .compile()
    )


class HourMinute(TimeAlike):
    EXAMPLES = [
        "12:34",
        "12:33am",
        "0888:34",
        "12:34  am",
        "12:34.",
    ]
    HOUR_MINUTE = (NAMED_HOUR + COLON + NAMED_MINUTE).join(ANYSPACE).group()
    hour_minute = (
        (HOUR_MINUTE + DOT.maybe()).group() + NAMED_APM.maybe()
    ).join_both_ends(ANYSPACE)
    PATTERN = hour_minute.compile()


class HourMinuteSpecial(TimeAlike):
    EXAMPLES = [
        "12:34 -",  # spaces are allowed between minute and negative
        "12:34 : ",
        "12:34- am",  # negative sign must be adjacent to either the preceding or succeeding element if apm is present
        "12:34 -Pm",
        "12:34 : am",
        "888:34- :",
        "12:34- : am",
        "12:33 -: am",
        "12:34. -",
        "12:34. -pm",
        "12:34.- Am",
    ]

    # fmt: off

    # two basic principles:
    # 1. the negative sign must be adjacent to either the preceding or succeeding element if apm is present
    # 2. the dot must be adjacent to the preceding element

    # {hour}:{minute} -  | {hour}:{minute} :
    hour_minute_single_char = (
        HourMinute.HOUR_MINUTE + ANYSPACE + (COLON | NAMED_SIGN)
    ).surround_anyspace()

    # {hour}:{minute}- {apm} | {hour}:{minute} -{apm} |  {hour}:{minute} : {apm}
    hour_minute_single_char_apm = (
        (HourMinute.HOUR_MINUTE + NAMED_SIGN + ANYSPACE + NAMED_APM).surround_anyspace()
        | (HourMinute.HOUR_MINUTE + ANYSPACE + NAMED_SIGN + NAMED_APM).surround_anyspace()
        | (HourMinute.HOUR_MINUTE + COLON + NAMED_APM).join_both_ends(ANYSPACE)
    )

    # {hour}:{minute} - : {amp}? | {hour}:{minute}. -{apm}? | {hour}:{minute}.- {apm}
    hour_minute_two_chars = (
        (HourMinute.HOUR_MINUTE + ANYSPACE + NAMED_SIGN + ANYSPACE + COLON + ANYSPACE + NAMED_APM.maybe()).surround_anyspace() 
        | (HourMinute.HOUR_MINUTE + DOT + ANYSPACE + NAMED_SIGN + NAMED_APM.maybe()).surround_anyspace()
        | (HourMinute.HOUR_MINUTE + DOT + NAMED_SIGN + ANYSPACE + NAMED_APM).surround_anyspace()
    )

    hour_space_minute_colon = (NAMED_HOUR + SOMESPACE + NAMED_MINUTE + COLON).join(ANYSPACE)


    PATTERN = (hour_minute_single_char | hour_minute_single_char_apm | hour_minute_two_chars | hour_space_minute_colon).clone().compile()
    # fmt: on


class HMDot(TimeAlike):
    EXAMPLES = [
        "12:34.",  # dot must be adjacent to the preceding element
        "12:34. aM",
    ]
    dot_maybe_apm = (
        HourMinute.HOUR_MINUTE + DOT + ANYSPACE + NAMED_APM.maybe()
    ).surround_anyspace()
    PATTERN = dot_maybe_apm.compile()


class MinuteSecondMicrosecond(TimeAlike):
    EXAMPLES = [
        "12 :34.567",
        "12: 34.567am",
        "0888:34.567",
        "12:34.567   Pm",
    ]

    # second.microsecond cannot join with anyspace
    MINUTE_SECOND = (
        (NAMED_MINUTE + COLON + (NAMED_SECOND + DOT + NAMED_MICROSECOND))
        .join(ANYSPACE)
        .group()
    )

    minute_second = (MINUTE_SECOND + ANYSPACE + NAMED_APM.maybe()).surround_anyspace()
    PATTERN = minute_second.compile()


class MinuteSecondMicrosecondNegative(TimeAlike):
    EXAMPLES = [
        "12:34.567- am",
        "12:34.567 -pm",
        "0888:34.567-",
    ]

    # the negative sign must be adjacent to either the preceding or succeeding element
    minute_second_negative = (
        MinuteSecondMicrosecond.MINUTE_SECOND
        + NAMED_SIGN
        + ANYSPACE
        + NAMED_APM.maybe()
    ).surround_anyspace() | (
        MinuteSecondMicrosecond.MINUTE_SECOND
        + ANYSPACE
        + NAMED_SIGN
        + NAMED_APM.maybe()
    ).surround_anyspace().clone()

    PATTERN = minute_second_negative.compile()


class HourMinuteSecond(TimeAlike):
    EXAMPLES = [
        " 12:34:56",
        "12 :34: 56am",
        "0888:34:56 ",
        "12:34:56   Pm",
        "12:34 56",
    ]
    # fmt: off
    HOUR_MINUTE_SECOND = (
        (NAMED_HOUR + COLON + NAMED_MINUTE + COLON + NAMED_SECOND).join(ANYSPACE)
        | (NAMED_HOUR + COLON + NAMED_MINUTE + SOMESPACE + NAMED_SECOND).join(ANYSPACE)
    ).clone().group()

    hour_minute_second = (HOUR_MINUTE_SECOND + NAMED_APM.maybe()).join_both_ends(ANYSPACE)
    # fmt: on

    PATTERN = hour_minute_second.compile()


class HMSDot(TimeAlike):
    EXAMPLES = [
        "12:34:56.",  # dot must be adjacent to the preceding element
        "12:34:56. aM",
    ]
    dot_maybe_apm = (
        HourMinuteSecond.HOUR_MINUTE_SECOND + DOT + ANYSPACE + NAMED_APM.maybe()
    ).surround_anyspace()
    PATTERN = dot_maybe_apm.compile()


class HourMinuteSecondSpecial(TimeAlike):
    # This class mirrors HourMinuteSpecial but handles time formats with hours, minutes and seconds.
    # It supports the same special characters (negative signs, dots, colons) and AM/PM indicators.

    EXAMPLES = [
        "12:34:56 -",  # spaces are allowed between minute and negative
        "12:34:56 : ",
        "12:34:56- am",  # negative sign must be adjacent to either the preceding or succeeding element if apm is present
        "12:34:56 -Pm",
        "12:34:56 : am",
        "888:34:56- :",
        "12:34:56- : am",
        "12:34:56 -: am",
        "12:34:56. -",
        "12:34:56. -pm",
        "12:34:56.- Am",
    ]

    # fmt: off

    # two basic principles:
    # 1. the negative sign must be adjacent to either the preceding or succeeding element if apm is present
    # 2. the dot must be adjacent to the preceding element

    # HOUR_MINUTE_SECOND -  | HOUR_MINUTE_SECOND. | HOUR_MINUTE_SECOND :
    hour_minute_single_char = (
        HourMinuteSecond.HOUR_MINUTE_SECOND + ANYSPACE + (COLON | NAMED_SIGN)
    ).surround_anyspace() | (HourMinuteSecond.HOUR_MINUTE_SECOND + DOT).surround_anyspace()

    # HOUR_MINUTE_SECOND- {apm} | HOUR_MINUTE_SECOND -{apm} | HOUR_MINUTE_SECOND. {apm} | HOUR_MINUTE_SECOND : {apm}
    hour_minute_single_char_apm = (
        (HourMinuteSecond.HOUR_MINUTE_SECOND + NAMED_SIGN + ANYSPACE + NAMED_APM).surround_anyspace()
        | (HourMinuteSecond.HOUR_MINUTE_SECOND + ANYSPACE + NAMED_SIGN + NAMED_APM).surround_anyspace()
        | (HourMinuteSecond.HOUR_MINUTE_SECOND + DOT + ANYSPACE + NAMED_APM).surround_anyspace()
        | (HourMinuteSecond.HOUR_MINUTE_SECOND + COLON + NAMED_APM).join_both_ends(ANYSPACE)
    )

    # HOUR_MINUTE_SECOND - : {amp}? | HOUR_MINUTE_SECOND. -{apm}? | HOUR_MINUTE_SECOND.- {apm}
    hour_minute_two_chars = (
        (HourMinuteSecond.HOUR_MINUTE_SECOND + ANYSPACE + NAMED_SIGN + ANYSPACE + COLON + ANYSPACE + NAMED_APM.maybe()).surround_anyspace() 
        | (HourMinuteSecond.HOUR_MINUTE_SECOND + DOT + ANYSPACE + NAMED_SIGN + NAMED_APM.maybe()).surround_anyspace()
        | (HourMinuteSecond.HOUR_MINUTE_SECOND + DOT + NAMED_SIGN + ANYSPACE + NAMED_APM).surround_anyspace()
    )


    PATTERN = (hour_minute_single_char | hour_minute_single_char_apm | hour_minute_two_chars).clone().compile()
    # fmt: on


class HourMinuteSecondMicrosecond(TimeAlike):
    EXAMPLES = [
        "12:34:56.789",
        "12:34:56.789am",
        "0888:34:56.789",
        "12:34:56.789   Pm",
    ]

    HOUR_MINUTE_SECOND_MICROSECOND = (
        (HourMinute.HOUR_MINUTE + COLON + (NAMED_SECOND + DOT + NAMED_MICROSECOND))
        .join(ANYSPACE)
        .group()
    )

    hour_minute_second_microsecond = (
        HOUR_MINUTE_SECOND_MICROSECOND + NAMED_APM.maybe()
    ).join_both_ends(ANYSPACE)

    PATTERN = hour_minute_second_microsecond.compile()


class HourMinuteSecondMicrosecondWeird(TimeAlike, WeirdFeature):
    EXAMPLES = ["44:01 12:34.", "1:33 22:333. am"]

    PATTERN = (
        (
            HourMinute.HOUR_MINUTE
            + SOMESPACE
            + NAMED_SECOND
            + COLON
            + (NAMED_MICROSECOND + DOT).group()
            + NAMED_APM.maybe()
        )
        .join(ANYSPACE)
        .group()
    ).compile()


class HourMinuteSecondMicrosecondNegative(TimeAlike):
    EXAMPLES = [
        "12:34:56.789 - am",
        "12:34:56.789 -pm",
        "0888:34:56.789 - ",
    ]

    # Note: the priciple that
    # the negative sign must be adjacent to either the preceding or succeeding element if apm is present
    # is not hold here
    hour_minute_second_microsecond_negative = (
        HourMinuteSecondMicrosecond.HOUR_MINUTE_SECOND_MICROSECOND
        + NAMED_SIGN.maybe()
        + NAMED_APM.maybe()
    ).join_both_ends(ANYSPACE)

    PATTERN = hour_minute_second_microsecond_negative.compile()


class TimeFeatureDateTimeOnly(TimeAlike): ...


class MinuteSecondMicrosecondDateTimeOnly(TimeFeatureDateTimeOnly):
    MINUTE_SECOND_MICROSECOND = (
        (
            NAMED_MINUTE + COLON + (NAMED_SECOND + COMMA + NAMED_MICROSECOND).group()
        ).join(ANYSPACE)
        + ANYSPACE
        + NAMED_APM.maybe()
    ).surround_anyspace()
    PATTERN = MINUTE_SECOND_MICROSECOND.compile()


class HMSAlikeWithSpecialFirstSepDateTimeOnly(TimeFeatureDateTimeOnly):
    template = (
        (
            NAMED_HOUR
            + Placeholder("sep")
            + NAMED_MINUTE
            + COLON
            + (NAMED_SECOND + DOT.maybe()).group()
            + NAMED_APM.maybe()
        )
        .join(ANYSPACE)
        .group()
    )

    @classmethod
    def validate(cls, groupdict: TimeDict) -> Optional[TimeDict]:
        groupdict["hour"] = groupdict["minute"]
        groupdict["minute"] = groupdict["second"]
        groupdict.pop("second")
        return groupdict


class HMSAlikeWithSpaceAsFirstSepDateTimeOnly(HMSAlikeWithSpecialFirstSepDateTimeOnly):
    EXAMPLES = ["12 34:56"]
    PATTERN = HMSAlikeWithSpecialFirstSepDateTimeOnly.template.format(
        sep=SOMESPACE
    ).compile()


class HMSAlikeWithHyphenAsFirstSepDateTimeOnly(HMSAlikeWithSpecialFirstSepDateTimeOnly):
    EXAMPLES = ["12 - 34 : 56"]
    PATTERN = HMSAlikeWithSpecialFirstSepDateTimeOnly.template.format(
        sep=Primitive.hyphen()
    ).compile()


class HMSAlikeWithSlashAsFirstSepDateTimeOnly(HMSAlikeWithSpecialFirstSepDateTimeOnly):
    EXAMPLES = ["12 / 34 : 56"]
    PATTERN = HMSAlikeWithSpecialFirstSepDateTimeOnly.template.format(
        sep=Primitive.slash()
    ).compile()


class HMSWithSpecialFirstSep(TimeAlike):
    TEMPLATE = (
        NAMED_HOUR
        + Placeholder("sep")
        + NAMED_MINUTE
        + COLON
        + NAMED_SECOND
        + NAMED_APM.maybe()
    ).join_both_ends(ANYSPACE)


class HMSWithSpaceAsFirstSep(HMSWithSpecialFirstSep):
    EXAMPLES = ["12 34:56 am", "12 34:56"]
    PATTERN = HMSWithSpecialFirstSep.TEMPLATE.format(sep=SOMESPACE).compile()


class HMSWithSlashAsFirstSep(HMSWithSpecialFirstSep, TimeFeatureDateTimeOnly):
    EXAMPLES = ["12 / 34 : 56"]
    PATTERN = HMSWithSpecialFirstSep.TEMPLATE.format(sep=Primitive.slash()).compile()


class HMSWithHyphenAsFirstSep(HMSWithSpecialFirstSep, TimeFeatureDateTimeOnly):
    EXAMPLES = ["12 - 34 : 56"]
    PATTERN = HMSWithSpecialFirstSep.TEMPLATE.format(sep=Primitive.hyphen()).compile()


class HourDateTimeOnly(TimeFeatureDateTimeOnly):
    PATTERN = (
        (Primitive.digits() + SOMESPACE + NAMED_HOUR + COLON + NAMED_APM.maybe())
        .join_both_ends(ANYSPACE)
        .compile()
    )


class MSMWithSpaceAsFirstSep(TimeAlike):
    EXAMPLES = ["12 34.56 am"]
    COUNTER_EXAMPLES = ["12 34.60 am", "12 34.56"]
    PATTERN = (
        (
            NAMED_MINUTE
            + SOMESPACE
            + (NAMED_SECOND + DOT + NAMED_MICROSECOND).group()
            # apm is required
            + NAMED_APM
        )
        .join_both_ends(ANYSPACE)
        .compile()
    )

    @classmethod
    def validate(cls, groupdict: TimeDict) -> Optional[TimeDict]:
        # Note: no typo here
        if util.get_second(groupdict["microsecond"]) is None:
            return None
        return groupdict


class HMSWithSpaceAsFirstSepWithAdditionalSuffix(TimeAlike):
    EXAMPLES = ["12 34:56.", "12 34:56. am", "12 34:56: am"]
    dot_maybe_apm = (
        (NAMED_HOUR + SOMESPACE + NAMED_MINUTE + COLON + NAMED_SECOND).join(ANYSPACE)
        + (DOT | (ANYSPACE + COLON + ANYSPACE).group()).group()
        + ANYSPACE
        + NAMED_APM.maybe()
    ).surround_anyspace()
    PATTERN = dot_maybe_apm.compile()


class MinuteSecondMicrosecondWeird(TimeAlike, WeirdFeature):
    EXAMPLES = ["12.34,567   Pm"]
    COUNTER_EXAMPLES = ["12.34,5677   Pm"]

    PATTERN = (
        (
            NAMED_MINUTE
            + DOT
            + NAMED_SECOND
            + COMMA
            + NAMED_MICROSECOND
            + ANYSPACE
            + NAMED_APM.maybe()
        )
        .surround_anyspace()
        .group()
    ).compile()

    @classmethod
    def validate(cls, groupdict: TimeDict) -> Optional[TimeDict]:
        if len(groupdict["microsecond"]) != 3:
            return None
        return groupdict
