from typing import Optional
from wizard.feature import WeirdFeature

from ...common.pattern import Primitive
from .base import ExcelDateTimeAlikeBase, ExcelDateTime, DatetimeDict
from .date_alike import *
from .time_alike import (
    HourMinute,
    MinuteSecondMicrosecond,
    HourMinuteSecond,
    HourMinuteSecondMicrosecond,
    WeirdHourDecimalMinuteInteger,
    WeirdHourDecimalMinuteMonthName,
    TimeAlike,
)


class TimeDateAlike(ExcelDateTimeAlikeBase):
    SEP = (
        (
            (Primitive.comma() + Primitive.somespace())
            | Primitive.slash()
            | Primitive.hyphen()
            | Primitive.somespace()
        )
        + Primitive.anyspace()
    ).compile()

    DATES_STARTWITH_LETTER = [
        MonthNameDayYear,
        MonthNameDay,
        MonthNameYear,
    ]
    DATES_STARTWITH_NUMBER = [
        DayMonthName,
        # MonthNumberDay>DayMonthNumber>YearMonthNumber
        MonthNumberDay,
        DayMonthNumber,
        YearMonthNumber,
        YearMonthNumberDay,
        DayMonthNameYear,
    ]
    DATES: list[DateAlike] = DATES_STARTWITH_LETTER + DATES_STARTWITH_NUMBER
    TIMES: list[TimeAlike] = [
        WeirdHourDecimalMinuteInteger,
        WeirdHourDecimalMinuteMonthName,
        MinuteSecondMicrosecond,
        HourMinuteSecondMicrosecond,
        HourMinuteSecond,
        HourMinute,
    ]

    @classmethod
    def match_sep(cls, content: str, idx: int) -> Optional[int]:
        if not (0 <= idx < len(content)):
            return None

        if matched := cls.SEP.match(content[idx:]):
            return idx + matched.end()
        return None

    @classmethod
    def is_space_at(cls, content: str, idx: int) -> bool:
        if not (0 <= idx < len(content)):
            return False
        return content[idx] == " "

    @classmethod
    def match_date(cls, content: str, dates: list[DateAlike]) -> Optional[DatetimeDict]:
        for date in dates:
            datedict = date.fullmatch(content)
            if datedict and date.is_datetime_valid(**datedict):
                return datedict
        return None

    @classmethod
    def fullmatch(cls, content: str) -> Optional[DatetimeDict]:
        for time in cls.TIMES:
            timedict, idx = time.match(content)
            if not timedict or not time.is_datetime_valid(**timedict):
                continue

            start = cls.match_sep(content, idx) or (
                idx - 1 if cls.is_space_at(content, idx - 1) else None
            )

            if start is not None:
                remainder = content[start:].lstrip()
                if datedict := cls.match_date(remainder, cls.DATES):
                    return datedict | timedict
            else:
                # Empty separator is valid only if time ends with a letter and date starts with a digit, or vice versa.
                datedict, remainder = None, content[idx:].lstrip()
                if content[idx - 1].isalpha():
                    datedict = cls.match_date(remainder, cls.DATES_STARTWITH_NUMBER)
                elif content[idx - 1].isdigit():
                    datedict = cls.match_date(remainder, cls.DATES_STARTWITH_LETTER)

                return datedict | timedict if datedict else None

        return None

    @classmethod
    def is_datetime_valid(cls, **kwargs: DatetimeDict) -> Optional[ExcelDateTime]:
        if not (date := DateAlike.is_datetime_valid(**kwargs)):
            return None
        if not (time := TimeAlike.is_datetime_valid(**kwargs)):
            return None
        return date + cls.to_delta(time)


class WeirdTimeDateAlike(TimeDateAlike, WeirdFeature):
    DATES_STARTWITH_LETTER = []
    DATES_STARTWITH_NUMBER = [MonthNumberDayYearDateTimeOnly]
    TIMES = [WeirdHourDecimalMinuteMonthName]
    DATES = DATES_STARTWITH_NUMBER + DATES_STARTWITH_LETTER
