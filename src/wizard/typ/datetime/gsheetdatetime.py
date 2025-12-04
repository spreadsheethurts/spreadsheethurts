from datetime import datetime
from typing import Optional, Self
from .base import DateTime
import re


# We use 1200 years as the cycle length since it's both close to 1000 and divisible by 400 (the minimum period)
_DAYS_IN_A_MILLENNIUM = 438291
_MILLENNIA = 1200


class GsheetDateTime(DateTime):
    __slots__ = "_millennia"

    def __new__(
        cls,
        year: int = datetime.today().year,
        month: int = 1,
        day: int = 1,
        hour: int = 0,
        minute: int = 0,
        second: int = 0,
        microsecond: int = 0,
        tzinfo: Optional[datetime.tzinfo] = None,
        *,
        fold: int = 0,
    ) -> Self:
        millennia = year // _MILLENNIA
        # zero is invalid value for datetime.datetime, so we make adjust_year = _MILLENIA + remainder
        adjusted_year = year % _MILLENNIA + _MILLENNIA

        obj = datetime.__new__(
            cls,
            adjusted_year,
            month,
            day,
            hour,
            minute,
            second,
            microsecond,
            tzinfo,
            fold=fold,
        )
        obj._millennia = millennia
        return obj

    @property
    def year(self) -> int:
        return (self._millennia - 1) * _MILLENNIA + super().year

    def toordinal(self) -> int:
        return super().toordinal() + (self._millennia - 1) * _DAYS_IN_A_MILLENNIUM

    @classmethod
    def strptime(cls, date_string: str, format: str) -> Self:
        format_pattern = format.replace(r"%Y", r"(?P<year>\d+)")
        format_pattern = re.sub(r"%(.|(:z))", ".*", format_pattern)
        if match := re.match(format_pattern, date_string):
            year = int(match.group("year"))
            adjusted_year = year % _MILLENNIA + _MILLENNIA
            dummy_date_string = (
                date_string[: match.start("year")]
                + f"{adjusted_year:04d}"
                + date_string[match.end("year") :]
            )
            dt = datetime.strptime(dummy_date_string, format)
            return cls(
                year,
                dt.month,
                dt.day,
                dt.hour,
                dt.minute,
                dt.second,
                dt.microsecond,
                dt.tzinfo,
                fold=dt.fold,
            )
        else:
            raise ValueError(f"Invalid date string: {date_string}")

    def strftime(self, format: str) -> str:
        if 0 <= self.year <= 9999:
            year = f"{self.year:04d}"
        else:
            year = f"{self.year}"
        format = format.replace("%Y", year)

        # Parent class DateTime requires %Y in the format, so we use std datetime's strftime
        return super(datetime, self).strftime(format)
