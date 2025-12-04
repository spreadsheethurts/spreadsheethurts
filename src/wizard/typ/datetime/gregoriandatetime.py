from datetime import datetime
import re
from typing import Self, Optional

from ..number import Int, Float
from convertdate import julianday, julian
from .base import DateTime

# We use 1200 years as the cycle length since it's both close to 1000 and divisible by 400 (the minimum period)
_DAYS_IN_A_MILLENNIUM = 438291
_MILLENNIA = 1200


class GregorianDateTime(DateTime):
    """Represents Gregorian datetimes, supporting arbitrarily large years and accurate historical calendar transitions.

    Unlike Python's standard `datetime` objects, which use a proleptic Gregorian calendar and are limited to years up to 9999,
    this class precisely replicates historical Gregorian calendar behavior. This includes:

    * **Julian Calendar Adherence (Pre-1582):** Dates before October 4, 1582, are calculated using the **Julian calendar**.
    * **Gregorian Calendar Adoption (Post-1582):** Dates on or after October 15, 1582, adhere to the **Gregorian calendar**.
        This accurately accounts for the **ten-day omission in October 1582** (specifically, October 5-14, 1582, never occurred).
        This correction was necessary because the Julian calendar's slight overestimation of the year's length (about 11 minutes and 14 seconds per year)
        had caused the calendar to drift. By 1582, the **vernal equinox**, which historically fell around March 21 (as established by the Council of Nicaea in **325 CE** for calculating Easter),
        had shifted to occur around March 11. To realign the calendar with the astronomical equinox and restore March 21 as its date, 10 accumulated "extra" days were removed.
        The number was 10, not 12 or any other number, specifically to bring the vernal equinox back to March 21.

    To accommodate **arbitrarily large years** while leveraging existing `datetime` functionality, this class employs the following internal representation:

    - _millennia: Stores a numerical representation of the millennium chunk, allowing for dates far beyond the standard `datetime` limit.
    - _isjulian: A boolean flag indicating whether the date falls within the Julian calendar period.
    - _extraday: An integer used to track an "extra day" that might arise from discrepancies in leap year rules between the Julian and Gregorian calendars
    (e.g., years divisible by 100 but not 400 were leap years in the Julian calendar but not the Gregorian).

    This design aims to maximize reuse of Python's robust `datetime` implementation while providing historical calendar accuracy.

    Raises:
        ValueError: If the date is invalid (e.g., 1582-10-5 to 1582-10-14)
        OverflowError: If the year is negative
    """

    __slots__ = ("_isjulian", "_extraday", "_millennia")

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
        if year <= 0:
            raise OverflowError("Year cannot be negative")

        if year == 1582 and month == 10 and 5 <= day <= 14:
            raise ValueError(
                "1582-10-5 to 1582-10-14 are invalid dates in the Gregorian calendar."
            )

        isjulian, extraday = False, 0
        if year < 1582 or (year == 1582 and (month < 10 or (month == 10 and day <= 4))):
            isjulian = True
            if year % 4 == 0 and month == 2 and day == 29:
                extraday = 1
                # let day be 28 to make datetime happy
                day -= 1

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
        obj._isjulian = isjulian
        obj._extraday = extraday
        obj._millennia = millennia
        return obj

    @property
    def year(self) -> int:
        """Get the actual year, combining millennia and datetime year."""
        return (self._millennia - 1) * _MILLENNIA + super().year

    @property
    def day(self) -> int:
        """Get the actual day, combining extraday and datetime day."""
        return super().day + self._extraday

    @staticmethod
    def _julian_toordinal(year, month, day) -> int:
        """Return the Julian ordinal for the year, month, and day."""
        base = julianday.from_julian(1, 1, 1)
        return int(julianday.from_julian(year, month, day) - base + 1)

    def toordinal(self) -> int:
        """Return the Gregorian ordinal for the year, month, and day."""
        if self._isjulian:
            return self._julian_toordinal(self.year, self.month, self.day)
        else:
            return (
                super().toordinal() + (self._millennia - 1) * _DAYS_IN_A_MILLENNIUM + 2
            )

    @classmethod
    def fromordinal(cls, n: int) -> Self:
        """Create a GregorianDateTime object from a Gregorian ordinal."""
        threshold = cls._julian_toordinal(1582, 10, 4)
        if n <= threshold:
            base = julianday.from_julian(1, 1, 1)
            jd = n + base - 1
            year, month, day = julian.from_jd(jd)
            return cls(year, month, day)
        else:
            return super().fromordinal(n - 2)

    @classmethod
    def strptime(cls, date_string: str, format: str) -> Self:
        """Parse a date string into a GregorianDateTime object.

        Only %Y, %m, and %d are supported.
        """
        format_pattern = (
            format.replace(r"%Y", r"(?P<year>\d+)")
            .replace(r"%m", r"(?P<month>\d{1,2})")
            .replace(r"%d", r"(?P<day>\d{1,2})")
        )
        format_pattern = re.sub(r"%(.|(:z))", ".*", format_pattern)
        dummy_date_string = date_string
        extraday = 0

        if match := re.match(format_pattern, date_string):
            groups = match.groupdict()
            year, month, day = (
                int(groups["year"]),
                int(groups["month"]),
                int(groups["day"]),
            )
            if month == 2 and day == 29:
                extraday = 1
                day -= 1
            # It's crucial to process the day before the year.
            # If the year has five digits, it could shift the day's expected location in the input
            dummy_date_string = (
                dummy_date_string[: match.start("day")]
                + f"{day:02d}"
                + dummy_date_string[match.end("day") :]
            )
            dummy_date_string = (
                dummy_date_string[: match.start("year")]
                + f"{year % _MILLENNIA + _MILLENNIA:04d}"
                + dummy_date_string[match.end("year") :]
            )
            dt = datetime.strptime(dummy_date_string, format)
            return cls(
                year,
                dt.month,
                dt.day + extraday,
                dt.hour,
                dt.minute,
                dt.second,
                dt.microsecond,
                dt.tzinfo,
                fold=dt.fold,
            )
        else:
            raise ValueError(f"Invalid date string {date_string} with format {format}")

    def strftime(self, format: str) -> str:
        """Format the date according to the format string.

        Only %Y and %d are supported.
        """
        # try to find year part and replace it with the actual year
        year_match = re.search(r"%Y", format)
        if not year_match:
            raise ValueError("format must contain %Y for year")

        if 0 <= self.year <= 9999:
            year = f"{self.year:04d}"
        else:
            year = f"{self.year}"

        format = format.replace("%Y", year)

        # try to find day part and replace it with the actual day
        day_match = re.search(r"%d", format)
        if day_match:
            format = format.replace("%d", f"{self.day:02d}")

        # Parent class DateTime requires %Y in the format, so we use std datetime's strftime
        return super(datetime, self).strftime(format)

    def to_number(
        self,
        other: Optional[datetime] = None,
        num_per_day: int = 1,
    ) -> Int | Float:
        if other is None:
            other = GregorianDateTime(1899, 12, 30, 0, 0, 0)
        return super().to_number(other, num_per_day)
