from typing import Any, Optional
from datetime import date

CURRENT_CENTURY = date.today().year // 100


class Month2Num:
    """Maps month names and abbreviations to month numbers."""

    def __init__(self) -> None:
        self.full = {
            "January": 1,
            "February": 2,
            "March": 3,
            "April": 4,
            "May": 5,
            "June": 6,
            "July": 7,
            "August": 8,
            "September": 9,
            "October": 10,
            "November": 11,
            "December": 12,
        }
        self.abbr = {
            "Jan": 1,
            "Feb": 2,
            "Mar": 3,
            "Apr": 4,
            "Jun": 6,
            "Jul": 7,
            "Aug": 8,
            "Sep": 9,
            "Oct": 10,
            "Nov": 11,
            "Dec": 12,
        }
        self.months = {**self.full, **self.abbr}

    def __getitem__(self, month: str | int) -> Optional[int]:

        def validate(month: int) -> Optional[int]:
            if 1 <= month <= 12:
                return month
            return None

        if isinstance(month, int):
            return validate(month)

        elif month.isdigit():
            if len(month) <= 2 and (value := validate(int(month))):
                return value
            else:
                return None

        month = month.lower().capitalize()
        # Account for abbreviated month names followed by a dot (e.g., Dec.) during month validation.
        # Note: Full names that are also abbreviations (e.g., May) are not considered valid in this dot-abbreviated format.
        if month.endswith("."):
            if (value := self.abbr.get(month[:-1])) and not self.full.get(month[:-1]):
                return value
        elif value := self.months.get(month):
            return value
        return None

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        return self.__getitem__(*args, **kwds)


class DateTimeUtils:
    def __init__(self) -> None:
        self.month2num = Month2Num()

    @property
    def max_year(self) -> int:
        """Returns the maximum year."""
        return 32767

    @property
    def min_year(self) -> int:
        """Returns the minimum year."""
        return 0

    @property
    def two_digit_year_cutoff(self) -> int:
        """Returns the cutoff year for interpreting two-digit years.

        Two-digit years less than this value are interpreted as 21st century years (20xx),
        while years greater than or equal to this value are interpreted as 20th century years (19xx).

        For example, with a cutoff of 30:
        - '29' is interpreted as 2029
        - '30' is interpreted as 1930
        """
        return 30

    def get_month(self, month: str | int) -> Optional[int]:
        """Returns corresponding integer if the month is valid, None otherwise.

        For string inputs:
            - Must be either:
                - A 1-2 digit number (e.g. "1", "01", "12") within range [1, 12]
                - A valid month name or abbreviation (e.g. "January", "Jan")
        For integer inputs:
            - Must be within range [1, 12]
        """
        return self.month2num[month]

    def get_day_of_week(self, day_of_week_sep: Optional[str]) -> bool:
        if day_of_week_sep is None:
            return True

        is_comma_sep = False
        if ", " in day_of_week_sep:
            day_of_week = day_of_week_sep.split(", ")[0].lower()
            is_comma_sep = True
        else:
            day_of_week = day_of_week_sep.split(" ")[0].lower()

        day_of_weeks = {
            "sunday",
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
        }

        day_of_weeks_abbr = {
            "sun",
            "mon",
            "tue",
            "wed",
            "thu",
            "fri",
            "sat",
        }

        if is_comma_sep:
            return day_of_week in day_of_weeks
        else:
            return day_of_week in (day_of_weeks_abbr | day_of_weeks)

    def get_year(self, year: str | int) -> Optional[int]:
        """Returns corresponding integer if the year is valid, None otherwise.

        For string inputs:
            - Years with value 0 must be 1-2 digits only
            - Years with leading zeros must be 6 digits or less
            - Apply integer validation
        For integer inputs:
            - Must be less than 1,000,000 and have a remainder less than 32,768 when divided by 65,536 (the remainder becomes the actual year)
        """

        def validate_one_or_two_digit_year(year: int) -> Optional[int]:
            if self.min_year <= year < self.two_digit_year_cutoff:
                return year + CURRENT_CENTURY * 100
            elif self.two_digit_year_cutoff <= year <= 99:
                return year + (CURRENT_CENTURY - 1) * 100
            return None

        def validate(year: int) -> Optional[int]:
            if (
                self.min_year <= year <= 1_000_000
                and (year := year % 65536) <= self.max_year
            ):
                return year
            return None

        if isinstance(year, str) and year.isdigit():
            # zero year must be represented with one or two digits only
            if int(year) == 0 and len(year) > 2:
                return None

            if len(year) == 1 or len(year) == 2:
                return validate_one_or_two_digit_year(int(year))

            if year.startswith("0"):
                # one or two-digit years are transformed to a year in either the current or previous century
                if len(year) == 1 or len(year) == 2:
                    return validate_one_or_two_digit_year(int(year))
                # reject years with leading zeros that are longer than 6 digits
                # (e.g. "0000000" is invalid, but "000042" is valid)
                elif len(year) > 6:
                    return None

            # other years are validated as normal
            # (e.g. "013" -> 13, "0013" -> 13)
            return validate(int(year))

        return validate(year)

    def get_day(self, day: str | int) -> Optional[int]:
        """Returns corresponding integer if the day is valid, None otherwise.

        For string inputs:
            - Must be 1-2 digits only (e.g. "1", "01", "31")
            - Must be within the range of [1, 31] when converted to integer
        For integer inputs:
            - Must be within the range of [1, 31]
        """

        def validate(day: int) -> Optional[int]:
            if 1 <= day <= 31:
                return day
            return None

        if isinstance(day, str) and day.isdigit():
            if len(day) <= 2 and (value := validate(int(day))):
                return value
            else:
                return None

        return validate(int(day))

    def _time_check_zero(self, value: str) -> bool:
        """Checks if the value is zero and has more than 2 digits."""
        if value.isdigit() and int(value) == 0 and len(value) > 2:
            return False
        return True

    def get_hour(self, hour: str | int) -> Optional[int]:
        if isinstance(hour, str) and not self._time_check_zero(hour):
            return None
        return int(hour)

    def _get_minute_or_second(self, value: str | int) -> Optional[int]:
        if isinstance(value, str) and not self._time_check_zero(value):
            return None

        return int(value)

    def get_minute(self, minute: str | int) -> Optional[int]:
        return self._get_minute_or_second(minute)

    def get_second(self, second: str | int) -> Optional[int]:
        return self._get_minute_or_second(second)

    def get_microsecond(self, microsecond: str | int) -> Optional[int]:
        if isinstance(microsecond, str):
            return float("." + microsecond) * 1e6
        return int(microsecond)

    def max_hour(self) -> int:
        return 1193046
