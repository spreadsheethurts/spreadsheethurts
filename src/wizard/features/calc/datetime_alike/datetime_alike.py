import re
from typing import Optional, Unpack
from enum import StrEnum

from .base import CalcDateTimeAlikeBase, DatetimeDict, TimeDict, DateDict

from wizard.utils.misc import roclassproperty
from wizard.typ import GregorianDateTime
from .date_alike import (
    MonthNumberDay,
    YearMonthNumberDayExpected,
    MonthNumberDayYear,
    YearMonthNameDay,
    DayMonthNameYear,
    MonthNameDayYear,
    MonthNameDayYear2,
    DateAlike,
    MonthNumberDayYearDateTimeOnly,
    MonthNumberDayDateTimeOnly,
    YearMonthNumberDateTimeOnly,
    MonthNumberDayYear2DateTimeOnly,
)
from .time_alike import (
    Hour,
    HourMinute,
    HMDot,
    HMSDot,
    MinuteSecondMicrosecond,
    HourMinuteSecond,
    HMSWithSpaceAsFirstSep,
    HMSWithSlashAsFirstSep,
    HMSWithHyphenAsFirstSep,
    HourMinuteSecondMicrosecond,
    MinuteSecondMicrosecondDateTimeOnly,
    TimeAlike,
    HMSAlikeWithSlashAsFirstSepDateTimeOnly,
    HMSAlikeWithSpaceAsFirstSepDateTimeOnly,
    HMSAlikeWithHyphenAsFirstSepDateTimeOnly,
    HourDateTimeOnly,
)


COMMON_TIMES: list[TimeAlike] = [
    Hour,
    HourMinute,
    HMDot,
    MinuteSecondMicrosecond,
    HourMinuteSecond,
    HMSDot,
    HourMinuteSecondMicrosecond,
]


class DateTimeSep(StrEnum):
    SLASH = "/"
    SPACE = " "
    HYPHEN = "-"
    COMMASPACE = ", "


def declare_seps(seps: list[DateTimeSep]) -> list[DateTimeSep]:
    # place the space at the end if seps contains space
    if DateTimeSep.SPACE in seps:
        seps.remove(DateTimeSep.SPACE)
        seps.append(DateTimeSep.SPACE)
    return seps


class DateTimeAlike(CalcDateTimeAlikeBase):

    DateTimeCombination: dict[DateAlike, tuple[list[TimeAlike], list[DateTimeSep]]] = {}

    @classmethod
    def is_datetime_valid(
        cls,
        **kwargs: Unpack[DatetimeDict],
    ) -> Optional[GregorianDateTime]:
        """Validates a datetime by checking if both its date and time parts are valid."""
        if not (date := DateAlike.is_datetime_valid(**kwargs)):
            return None
        if not (time := TimeAlike.is_datetime_valid(datetime=True, **kwargs)):
            return None
        return date + cls.to_delta(time)

    @classmethod
    def is_sep_valid_at(cls, s: str, index: int, seps: list[DateTimeSep]) -> bool:
        """Checks if the character at the specified index is a valid separator ( - or / )."""
        return 0 <= index < len(s) and any(s[index:].startswith(sep) for sep in seps)

    @classmethod
    def validate_timedict(cls, timedict: TimeDict) -> Optional[TimeDict]:
        return timedict

    @classmethod
    def validate_datedict(cls, datedict: DateDict) -> Optional[DateDict]:
        return datedict

    @classmethod
    def get_time_remainder(cls, s: str, start: int) -> Optional[str]:
        return s[start:].strip()

    @classmethod
    def fullmatch(cls, s: str) -> Optional[DatetimeDict]:
        """Match a datetime string composed of a date and time, separated by spaces.

        This method attempts to parse the datetime by first matching the date component,
        followed by the time component. The date and time must appear in the correct order.
        """
        for date, (times, seps) in cls.DateTimeCombination.items():
            datedict, index = date.match(s)
            if (
                not datedict
                or not cls.validate_datedict(datedict)
                or not date.is_datetime_valid(**datedict)
            ):
                continue
            if cls.is_sep_valid_at(s, index, seps):
                remainder = cls.get_time_remainder(s, index + 1)
            # Some date features, like MonthNameDayYear may consume sep like '/'
            elif cls.is_sep_valid_at(s, index - 1, seps):
                remainder = cls.get_time_remainder(s, index)
            else:
                continue

            if not remainder:
                continue

            for time in times:
                if (
                    (timedict := time.fullmatch(remainder))
                    and cls.validate_timedict(timedict)
                    and time.is_datetime_valid(**timedict)
                ):
                    return datedict | timedict
        return None

    @roclassproperty
    def EXAMPLES(cls) -> list[str]:
        """Calculate the datetime examples by combining the date and time examples."""
        return [
            f"{de}{sep}{te}"
            for date, (times, seps) in cls.DateTimeCombination.items()
            for time in times
            for sep in seps
            for de in date.EXAMPLES
            for te in time.EXAMPLES
        ]

    @classmethod
    def inclusive_debug(cls):
        for date, (times, seps) in cls.DateTimeCombination.items():
            for time in times:
                for sep in seps:
                    for de in date.EXAMPLES:
                        for te in time.EXAMPLES:
                            print(
                                date.__qualname__,
                                time.__qualname__,
                                sep,
                                f"{de}{sep}{te}",
                                sep="\t",
                            )


class DateTimeWithNumericMonth(DateTimeAlike):
    """Match a datetime string where date is composed of a numeric month."""

    TIMES = COMMON_TIMES + [
        HMSAlikeWithSlashAsFirstSepDateTimeOnly,
        HMSAlikeWithSpaceAsFirstSepDateTimeOnly,
    ]
    ALL_TIMES = TIMES + [
        HMSAlikeWithHyphenAsFirstSepDateTimeOnly,
    ]
    DateTimeCombination: dict[DateAlike, list[TimeAlike]] = {
        MonthNumberDay: (
            TIMES,
            [DateTimeSep.SPACE],
        ),
        MonthNumberDayYear: (
            TIMES,
            [DateTimeSep.SPACE],
        ),
        MonthNumberDayYearDateTimeOnly: (
            ALL_TIMES,
            [DateTimeSep.SLASH, DateTimeSep.HYPHEN, DateTimeSep.SPACE],
        ),
        YearMonthNumberDayExpected: (
            ALL_TIMES,
            [DateTimeSep.SLASH, DateTimeSep.HYPHEN, DateTimeSep.SPACE],
        ),
    }


class DateTimeWithNamedMonth(DateTimeAlike):
    """Match a datetime string where date is composed of a named month."""

    # DayMonthNameYear has higher priority than YearMonthNameDay.

    TIMES = COMMON_TIMES + [HMSWithSpaceAsFirstSep, HMSWithSlashAsFirstSep]
    DateTimeCombination: dict[DateAlike, list[TimeAlike]] = {
        DayMonthNameYear: (TIMES + [HMSWithHyphenAsFirstSep], [DateTimeSep.SPACE]),
        YearMonthNameDay: (TIMES + [HMSWithHyphenAsFirstSep], [DateTimeSep.SPACE]),
        MonthNameDayYear: (TIMES, [DateTimeSep.COMMASPACE, DateTimeSep.SPACE]),
        MonthNameDayYear2: (TIMES, [DateTimeSep.COMMASPACE, DateTimeSep.SPACE]),
    }


class ISO8601DateTimeBase(DateTimeAlike):
    """Match a datetime string in ISO 8601 format with a 'T' separator.

    More details: https://en.wikipedia.org/wiki/ISO_8601#Combined_date_and_time_representations
    """

    @classmethod
    def fullmatch(cls, s: str) -> Optional[DatetimeDict]:
        """Match a datetime string composed of a date and time, separated by a 'T'.

        The date must be in MonthNumberDayYear/YearMonthNumberDay format , with no leading or trailing whitespace.
        The time may include trailing spaces, but must not have leading spaces.
        """
        for date, (times, _) in cls.DateTimeCombination.items():
            datedict, index = date.match(s)
            if not datedict or not date.is_datetime_valid(**datedict):
                continue

            if (
                s[index - 1] == " "
                or s.startswith(" ")
                # make sure index is not out of range
                or len(s) == index
                or s[index] != "T"
            ):
                return None

            remainder = s[index + 1 :]
            for time in times:
                if (timedict := time.fullmatch(remainder)) and time.is_datetime_valid(
                    **timedict
                ):
                    return cls.validate(datedict | timedict)
        return None

    @roclassproperty
    def EXAMPLES(cls) -> list[str]:
        """Calculate ISO 8601 datetime examples with apm notation.

        Although ISO 8601 uses the 24-hour format, providing examples with apm notation can make
        subclassing and customization more concise.
        """

        return [
            f"{de}T{te}"
            for date, (times, _) in cls.DateTimeCombination.items()
            for time in times
            for de in date.EXAMPLES
            for te in time.EXAMPLES
            if not de.startswith(" ")
            and not de.endswith(" ")
            and not te.startswith(" ")
        ]


class ISO8601DateTimeWithApm(ISO8601DateTimeBase):
    """Match a datetime string in ISO 8601 format with a 'T' separator, including an 'apm' group."""

    TIMES: list[TimeAlike] = [
        HMDot,
        HMSDot,
        Hour,
        HourMinute,
        HourMinuteSecond,
        HourMinuteSecondMicrosecond,
        MinuteSecondMicrosecond,
        MinuteSecondMicrosecondDateTimeOnly,
        HMSAlikeWithSlashAsFirstSepDateTimeOnly,
        HMSAlikeWithSpaceAsFirstSepDateTimeOnly,
        HMSAlikeWithHyphenAsFirstSepDateTimeOnly,
        HourDateTimeOnly,
    ]
    DateTimeCombination = {
        MonthNumberDayYearDateTimeOnly: (
            TIMES,
            [],
        ),
        YearMonthNumberDayExpected: (
            TIMES,
            [],
        ),
    }


class ISO8601DateTime(ISO8601DateTimeBase):
    TIMES: list[TimeAlike] = [
        HMSAlikeWithSpaceAsFirstSepDateTimeOnly,
        HMSAlikeWithHyphenAsFirstSepDateTimeOnly,
    ]
    DateTimeCombination = {
        MonthNumberDayYearDateTimeOnly: (
            TIMES,
            [],
        ),
        YearMonthNumberDayExpected: (
            TIMES,
            [],
        ),
    }

    @classmethod
    def validate(cls, groupdict: DatetimeDict) -> DatetimeDict | None:
        return groupdict if groupdict.get("apm") is None else None

    @roclassproperty
    def EXAMPLES(cls) -> list[str]:
        return list(
            filter(lambda x: re.search(r"[apAP][mM]", x) is None, super().EXAMPLES)
        )


class PartialDateWithTime(DateTimeAlike):
    DateTimeCombination = {
        MonthNumberDayYear2DateTimeOnly: (
            COMMON_TIMES,
            [DateTimeSep.SLASH, DateTimeSep.SPACE],
        ),
        MonthNumberDayDateTimeOnly: (
            COMMON_TIMES,
            [DateTimeSep.HYPHEN],
        ),
        YearMonthNumberDateTimeOnly: (
            COMMON_TIMES,
            [DateTimeSep.HYPHEN],
        ),
    }

    @classmethod
    def validate_timedict(cls, timedict: TimeDict) -> Optional[TimeDict]:
        primary = timedict.get("hour") or timedict.get("minute")
        if primary and len(primary) <= 2 and 1 <= int(primary) <= 31:
            return timedict
        return None

    @classmethod
    def get_time_remainder(cls, s: str, start: int) -> Optional[str]:
        if s[start:].startswith(" "):
            return None
        return s[start:]
