from typing import Optional, Union
from datetime import date
from wizard.utils import classic_round


class Month2Num:
    """Maps month names, month name prefixes (3+ chars), and digits (1-12) to month numbers."""

    def __init__(self) -> None:
        self.months = [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]

    def __getitem__(self, month: str | int) -> Optional[int]:
        """Returns the month number (1-12) for a given month name, digit, or prefix.

        If the month is a digit, it must be one or two digits.
        Otherwise, it must be a month name, abbreviation, or prefix that exceeds 2 characters in length.
        """
        if isinstance(month, int):
            if 1 <= month <= 12:
                return month
            return None

        if month.isdigit():
            if len(month) > 2:
                return None

            month = int(month)
            if 1 <= month <= 12:
                return month
            else:
                return None

        if len(month) < 3:
            return None

        month = month.lower().capitalize()
        for i, m in enumerate(self.months):
            if month in m:
                return i + 1


month2num = Month2Num()
CURRENT_CENTURY = date.today().year // 100


class DateTimeUtils:
    """Utility functions for date and time."""

    def month2num(self, month: str | int) -> Optional[int]:
        """Converts month names, abbreviations, and digits into corresponding month numbers, returning None upon conversion failure."""
        return month2num[month]

    def is_leap_year(self, year: int) -> bool:
        """Determines if the year is a leap year."""
        return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)

    def get_year(self, year: int | str) -> Optional[int]:
        """Determines if the year is valid within specified ranges.

        Returns True if the year is either one, two, or four digits and falls within the
        range of 1900-9999 for four-digit years or 0-99 for one or two-digit years.
        """

        def validate_one_or_two_digit_year(x: int):
            if 0 <= x < self.two_digit_year_cutoff:
                return x + CURRENT_CENTURY * 100
            elif self.two_digit_year_cutoff <= x <= 99:
                return x + (CURRENT_CENTURY - 1) * 100
            return None

        def validate(x: int):
            if self.min_year <= x <= self.max_year:
                return x
            return None

        if isinstance(year, str) and year.isdigit():
            # one or two-digit year
            if len(year) == 2 or len(year) == 1:
                return validate_one_or_two_digit_year(int(year))
            # four-digit year
            elif len(year) == 4:
                return validate(int(year))

            return None

        return validate(year)

    def get_month(self, month: int | str) -> Optional[int]:
        """Determines if month number, digit, and name is valid.

        Month numbers are in the range 1-12 while digits are in the range 01-12.
        """
        return self.month2num(month)

    def get_day(self, day: int | str) -> bool:
        """Determines if the day is valid within specified ranges..

        Day numbers are in the range 1-31 while digits are in the range 01-31.
        """

        def validate(x: int):
            if 1 <= x <= 31:
                return x
            return None

        if isinstance(day, str):
            if len(day) <= 2:
                return validate(int(day))
            return None

        return validate(day)

    @property
    def max_year(self) -> int:
        """Returns the maximum year."""
        return 9999

    @property
    def min_year(self) -> int:
        """Returns the minimum year."""
        return 1900

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

    def validate_digit_within_bounds(self, digit: str, lower: int, upper: int) -> bool:
        """Validate whether the given digit has at most one leading zero, or is '00', and falls within the specified range."""
        # Check if the digit is exactly '00'
        if digit == "00":
            return True

        # Check if there's more than one leading zero
        if digit.startswith("00"):
            return False

        # Check if the digit falls within the specified range
        return lower <= int(digit) <= upper

    def is_time_valid(self, time: int | str, bound_check: bool = True) -> bool:
        """Determines if the given time is valid within specified ranges."""
        # 1. "0" or "00" - "09" or "0100" - "0999"
        if isinstance(time, str):
            if time.startswith("0"):
                if len(time) == 1 or len(time) == 2:
                    return True
                elif time[1] != "0" and len(time) == 4:
                    return True

                return False

        if bound_check:
            time = int(time)
            return 0 <= time <= self.max_time
        else:
            return True

    def is_hour_valid(self, hour: int | str) -> bool:
        """Determines if the hour is valid within specified ranges."""
        return self.is_time_valid(hour)

    def is_minute_valid(self, minute: int | str) -> bool:
        """Determines if the minute is valid within specified ranges."""
        return self.is_time_valid(minute)

    def is_second_valid(self, second: int | str) -> bool:
        """Determines if the second is valid within specified ranges."""
        return self.is_time_valid(second)

    def _cast_time(self, digit: Union[str, int]) -> Optional[int]:
        """Converts a given digit input to a valid integer value.

        - If the digit is a string with leading zeros (e.g., "00", "09", "0999"), it will be within the range 0-9.
        - If the digit is a string without leading zeros, it will be converted directly to an integer.
        - If the conversion fails due to an invalid format, the function returns `None`.
        """
        if self.is_time_valid(digit):
            return int(digit)

        return None

    def get_hour(self, hour: Union[str, int]) -> Optional[int]:
        """Converts a given input to a valid integer hour value."""
        return self._cast_time(hour)

    def get_minute(self, minute: Union[str, int]) -> Optional[int]:
        """Converts a given input to a valid integer minute value."""
        return self._cast_time(minute)

    def get_second(self, second: Union[str, int]) -> Optional[int]:
        """Converts a given input to a valid integer second value."""
        return self._cast_time(second)

    def get_microsecond(self, microsecond: Union[str, int]) -> Optional[int]:
        """Converts a given input to a valid integer microsecond value."""
        if isinstance(microsecond, str):
            three_digits_microsecond = classic_round(float("." + microsecond) * 1e3)
            return three_digits_microsecond * 1e3
        return int(microsecond)

    @property
    def max_time(self) -> int:
        """Returns the maximum time."""
        return 9999

    @property
    def max_hour(self) -> int:
        """Returns the maximum hour."""
        return 9999

    @property
    def max_minute(self) -> int:
        """Returns the maximum minute."""
        return 9999

    @property
    def max_second(self) -> int:
        """Returns the maximum second."""
        return 9999

    def is_zero_valid(self, digit: str) -> bool:
        """The given digit is considered valid if it is either '0' or '00'."""
        return digit == "0" or digit == "00"
