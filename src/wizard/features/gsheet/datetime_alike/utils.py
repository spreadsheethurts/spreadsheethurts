from typing import Optional
from datetime import date

CURRENT_CENTURY = date.today().year // 100


class Month2Num:
    def __init__(self) -> None:
        self.months = {
            "January": 1,
            "Jan": 1,
            "February": 2,
            "Feb": 2,
            "March": 3,
            "Mar": 3,
            "April": 4,
            "Apr": 4,
            "May": 5,
            "June": 6,
            "Jun": 6,
            "July": 7,
            "Jul": 7,
            "August": 8,
            "Aug": 8,
            "September": 9,
            "Sep": 9,
            "October": 10,
            "Oct": 10,
            "November": 11,
            "Nov": 11,
            "December": 12,
            "Dec": 12,
        }

    def __getitem__(self, month: str | int) -> Optional[int]:
        if isinstance(month, int):
            if 1 <= month <= 12:
                return month
            return None

        if month.isdigit() and len(month) <= 2:
            if 1 <= int(month) <= 12:
                return int(month)
            else:
                return None

        month = month.lower().capitalize()
        if value := self.months.get(month):
            return value
        return None


class DateTimeUtils:
    def __init__(self) -> None:
        self.month2num = Month2Num()

    @property
    def max_year(self) -> int:
        """Returns the maximum year."""
        return 99999

    @property
    def min_year(self) -> int:
        """Returns the minimum year."""
        return 0

    @property
    def two_digit_year_cutoff(self) -> int:
        """Returns the cutoff year for interpreting two-digit years.

        Two-digit years less than this value are interpreted as 21st century years (20xx),
        while years greater than or equal to this value are interpreted as 20th century years (19xx).
        """
        return 30

    def get_month(self, month: str | int) -> Optional[int]:
        return self.month2num[month]

    def get_day_of_week(self, day_of_week: Optional[str]) -> bool:
        if day_of_week is None:
            return True

        day_of_weeks = {
            "sunday",
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sun",
            "mon",
            "tue",
            "wed",
            "thu",
            "fri",
            "sat",
        }
        if day_of_week.lower() in day_of_weeks:
            return True
        return False

    def get_year(self, year: str | int) -> Optional[int]:
        """Returns the year as an integer if valid; otherwise, returns None.

        For string inputs:
        - Leading zeros are removed.
        - Years less than 100 are interpreted in the current or last century.
        - All other years undergo a validity check.
        """

        def validate(year: int) -> Optional[int]:
            if self.min_year <= year <= self.max_year:
                return year
            return None

        def validate_one_or_two_digit_year(year: int) -> Optional[int]:
            if self.min_year <= year < self.two_digit_year_cutoff:
                return year + CURRENT_CENTURY * 100
            elif self.two_digit_year_cutoff <= year <= 99:
                return year + (CURRENT_CENTURY - 1) * 100
            return None

        if isinstance(year, str) and year.isdigit():
            year = int(year)
            if 0 <= year <= 99:
                return validate_one_or_two_digit_year(year)
            else:
                return validate(year)

        return validate(year)

    def get_day(self, day: str | int) -> Optional[int]:
        def is_valid(day: int) -> bool:
            return 1 <= day <= 31

        if isinstance(day, int):
            if is_valid(day):
                return day
            return None

        if day.isdigit():
            if len(day) <= 2 and is_valid(int(day)):
                return int(day)

        return None

    def _get_time(self, time: str | int, width: int) -> Optional[int]:
        time = int(time)
        min, max = -(2 ** (width - 1)), 2 ** (width - 1) - 1
        if min <= time <= max:
            return time
        return None

    def get_hour(self, hour: str | int) -> Optional[int]:
        return int(hour)

    def get_minute(self, minute: str | int) -> Optional[int]:
        # internal gsheet use int32 to store minute
        return self._get_time(minute, 32)

    def get_second(self, second: str | int) -> Optional[int]:
        return self._get_time(second, 32)

    def get_microsecond(self, microsecond: str | int) -> Optional[int]:
        # Google Sheets stores microseconds with nine digits of precision, but Python's datetime type is limited to six
        if isinstance(microsecond, str):
            if len(microsecond) > 11:
                return None
            return float("." + microsecond) * 1e6

        return int(microsecond)
