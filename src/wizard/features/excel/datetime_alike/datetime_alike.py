from typing import Optional

from wizard.feature import WeirdFeature

from .base import ExcelDateTimeAlikeBase, ExcelDateTime, DatetimeDict
from .date_alike import *
from .time_alike import *


class DateTimeAlike(ExcelDateTimeAlikeBase):
    DATES: list[DateAlike] = [
        MonthNameDayYear,
        MonthNameDay,
        MonthNameYear,
        DayMonthName,
        # MonthNumberDay>DayMonthNumber>YearMonthNumber
        MonthNumberDay,
        DayMonthNumber,
        YearMonthNumber,
        YearMonthNumberDay,
        DayMonthNameYear,
    ]
    TIMES: list[TimeAlike] = [
        WeirdHourDecimalMinuteInteger,
        WeirdHourDecimalMinuteMonthName,
        MinuteSecondMicrosecond,
        HourMinuteSecondMicrosecond,
        HourMinuteSecond,
        HourMinute,
    ]

    @classmethod
    def is_space_at(cls, content: str, index: int) -> bool:
        if not (0 <= index < len(content)):
            return False

        return content[index] == " "

    @classmethod
    def fullmatch(cls, content: str) -> Optional[DatetimeDict]:
        for date in cls.DATES:
            datedict, idx = date.match(content)
            if not datedict or not date.is_datetime_valid(**datedict):
                continue

            if cls.is_space_at(content, idx - 1):
                remainder = content[idx:].lstrip()
                for time in cls.TIMES:
                    timedict = time.fullmatch(remainder)
                    if timedict and time.is_datetime_valid(**timedict):
                        return datedict | timedict

        return None

    @classmethod
    def is_datetime_valid(cls, **kwargs: DatetimeDict) -> Optional[ExcelDateTime]:
        if not (date := DateAlike.is_datetime_valid(**kwargs)):
            return None
        if not (time := TimeAlike.is_datetime_valid(**kwargs)):
            return None
        return date + cls.to_delta(time)


class WeirdDateTimeAlike(DateTimeAlike, WeirdFeature):
    DATES = [MonthNumberDayYearDateTimeOnly]
    TIMES = [WeirdHourDecimalMinuteMonthName]
