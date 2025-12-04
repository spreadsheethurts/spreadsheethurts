import operator
from datetime import datetime, timedelta
from typing import Callable, Self, Union
from ..number import Int, Float


class DateTime(datetime):

    def _binary(self, op: Callable[[int, int], bool], other: Self) -> bool:
        if isinstance(other, DateTime):
            return op(self.to_number(other), 0)
        return NotImplemented

    __eq__ = lambda self, other: self._binary(operator.eq, other)
    __lt__ = lambda self, other: self._binary(operator.lt, other)
    __le__ = lambda self, other: self._binary(operator.le, other)
    __gt__ = lambda self, other: self._binary(operator.gt, other)
    __ge__ = lambda self, other: self._binary(operator.ge, other)

    def __sub__(self, other: Union[datetime, timedelta]) -> timedelta:
        if isinstance(other, timedelta):
            return self + (-other)
        elif isinstance(other, datetime):
            days = self.toordinal() - other.toordinal()
            seconds = (
                self.hour * 3600
                + self.minute * 60
                + self.second
                - other.hour * 3600
                - other.minute * 60
                - other.second
            )
            return timedelta(
                days=days,
                seconds=seconds,
                microseconds=self.microsecond - other.microsecond,
            )

    def __add__(self, other: timedelta) -> Self:
        delta = (
            timedelta(
                self.toordinal(),
                hours=self.hour,
                minutes=self.minute,
                seconds=self.second,
                microseconds=self.microsecond,
            )
            + other
        )
        hour, rem = divmod(delta.seconds, 3600)
        minute, second = divmod(rem, 60)
        date = self.fromordinal(delta.days)
        return self.__class__(
            date.year,
            date.month,
            date.day,
            hour=hour,
            minute=minute,
            second=second,
            microsecond=delta.microseconds,
            tzinfo=self.tzinfo,
            fold=self.fold,
        )

    @classmethod
    def from_datetime(cls, dt: datetime) -> Self:
        return cls(
            dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.microsecond
        )

    def toordinal(self) -> int:
        return super().toordinal()

    @classmethod
    def fromordinal(cls, n: int) -> Self:
        return super().fromordinal(n)

    @classmethod
    def strptime(cls, date_string: str, format: str) -> Self:
        return super().strptime(date_string, format)

    def strftime(self, format: str) -> str:
        if "%Y" not in format:
            raise ValueError("format must contain %Y for year")

        # `strftime('%Y')` in datetime doesn't zero-pad years less than 1000 (e.g., it produces '100').
        # This causes parsing failures with `strptime`, so we manually format a four-digit year.
        format = format.replace("%Y", f"{self.year:04d}")
        return super().strftime(format)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}({self.year}, {self.month}, {self.day}, "
            f"{self.hour}, {self.minute}, {self.second}, "
            f"{self.microsecond})"
        )

    def __str__(self) -> str:
        return self.strftime("%Y-%m-%d %H:%M:%S.%f")

    @staticmethod
    def timedelta_to_number(delta: timedelta, num_per_day: int = 1) -> Int | Float:
        num = delta.total_seconds() * num_per_day / (24 * 3600)
        return Int(num) if num.is_integer() else Float(num)

    @staticmethod
    def number_to_timedelta(number: float | int, num_per_day: int = 1) -> timedelta:
        return timedelta(seconds=number * (24 * 3600) / num_per_day)

    def to_number(self, other: datetime, num_per_day: int = 1) -> Int | Float:
        return self.timedelta_to_number(self - other, num_per_day)

    @classmethod
    def with_overflow_times(
        cls,
        year: int = 1900,
        month: int = 1,
        day: int = 0,
        hour: int = 0,
        minute: int = 0,
        second: int = 0,
        microsecond: int = 0,
    ) -> Self:
        """Create a datetime instance, automatically handling time carry-over.

        This method allows time components like `hour`, `minute` and `second` to
        exceed their normal range. The overflow is automatically added to the next
        largest unit. For example, `hour=25` is correctly handled as 1 AM the next
        day.
        """
        # Normalize the time values
        total_seconds = hour * 3600 + minute * 60 + second + microsecond / 1_000_000
        total_minutes = total_seconds // 60
        total_hours = total_minutes // 60

        # Calculate the new time values
        microsecond = int(microsecond % 1_000_000)
        second = int(total_seconds % 60)
        minute = int(total_minutes % 60)
        hour = int(total_hours % 24)

        # Calculate the number of days to add
        extra_days = total_hours // 24
        if day == 0:
            day = 1
            extra_days -= 1
        date = cls(year, month, day) + timedelta(days=extra_days)

        # Return the final datetime object
        return cls(
            year=date.year,
            month=date.month,
            day=date.day,
            hour=hour,
            minute=minute,
            second=second,
            microsecond=microsecond,
        )

    def days_since_1900(self) -> Int | Float:
        base = self.__class__(1899, 12, 30, 0, 0, 0)
        return self.timedelta_to_number(self - base)

    def days_since_1904(self) -> Int | Float:
        base = self.__class__(1904, 1, 1, 0, 0, 0)
        return self.timedelta_to_number(self - base)

    def __deepcopy__(self, *args, **kwargs):
        return self.__new__(
            self.__class__,
            self.year,
            self.month,
            self.day,
            self.hour,
            self.minute,
            self.second,
            self.microsecond,
        )
