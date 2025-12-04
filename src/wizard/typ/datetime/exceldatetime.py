from datetime import datetime
from typing import Optional, Self
import re

from ..number import Int, Float
from .base import DateTime


class ExcelDateTime(DateTime):
    """Represents Excel datetimes, handling its peculiar treatment of 1900 as a leap year (a classic example of a "bug-as-a-feature")."""

    __slots__ = "_extraday"

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
    ):
        extraday = 0
        # ExcelDateTime considers 1899-12-31 as 1900-1-0
        if (year, month, day) in ((1899, 12, 31), (1900, 1, 0)):
            year, month, day, extraday = 1900, 1, 1, -1

        if year < 1900 or year > 9999:
            raise OverflowError("Year must be between 1900 and 9999")

        if (year, month, day) == (1900, 2, 29):
            extraday, day = 1, 28

        obj = datetime.__new__(
            cls,
            year,
            month,
            day,
            hour,
            minute,
            second,
            microsecond,
            tzinfo,
            fold=fold,
        )
        obj._extraday = extraday
        return obj

    @property
    def day(self) -> int:
        return super().day + self._extraday

    def toordinal(self) -> int:
        threshold = datetime(1900, 2, 28).toordinal()
        # The parent's toordinal() method doesn't use this subclass's state (e.g. day),
        # so we manually add our day adjustment to the final ordinal value.
        ordinal = super().toordinal()
        if ordinal < threshold or (ordinal == threshold and not self._extraday):
            return ordinal + self._extraday
        else:
            return ordinal + 1

    @classmethod
    def fromordinal(cls, n: int) -> Self:
        threshold = datetime(1900, 2, 28).toordinal()
        if n <= threshold:
            return super().fromordinal(n)
        elif n == threshold + 1:
            return cls(1900, 2, 29)
        else:
            return super().fromordinal(n - 1)

    @classmethod
    def strptime(cls, date_string: str, format: str) -> Self:
        format_pattern = format.replace(r"%d", r"(?P<day>\d{1,2})").replace(
            r"%m", r"(?P<month>\d{1,2})"
        )
        format_pattern = re.sub(r"%(.|(:z))", ".*", format_pattern)
        dummy_date_string, extraday = date_string, 0
        if match := re.match(format_pattern, dummy_date_string):
            month, day = int(match.group("month")), int(match.group("day"))
            if month == 2 and day == 29:
                extraday = 1
                day -= 1
            dummy_date_string = (
                dummy_date_string[: match.start("day")]
                + f"{day:02d}"
                + dummy_date_string[match.end("day") :]
            )
            dt = super().strptime(dummy_date_string, format)
            return cls(
                dt.year,
                dt.month,
                dt.day + extraday,
                dt.hour,
                dt.minute,
                dt.second,
                dt.microsecond,
            )
        else:
            raise ValueError(f"Invalid date string: {date_string}")

    def strftime(self, format: str) -> str:
        if self._extraday:
            if match := re.search(r"%d", format):
                format = format.replace(match.group(0), f"{self.day:02d}")
        return super().strftime(format)

    def days_since_1900(self) -> Int | Float:
        base = self.__class__(1900, 1, 0, 0, 0, 0)
        return self.timedelta_to_number(self - base)

    def days_since_1904(self) -> Int | Float:
        base = self.__class__(1904, 1, 1, 0, 0, 0)
        return self.timedelta_to_number(self - base)
