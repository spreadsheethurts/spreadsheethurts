from collections import OrderedDict
from typing import Optional, TypedDict, Literal, Unpack, overload, Type
from datetime import timedelta

from wizard.feature import Feature
from wizard.typ import DateTime


class DatetimeDict(TypedDict):
    year: Optional[str | int]
    month: Optional[str | int]
    day: Optional[str | int]
    hour: Optional[str | int]
    minute: Optional[str | int]
    second: Optional[str | int]
    microsecond: Optional[str | int]
    apm: Optional[Literal["am", "pm", "AM", "PM", "aM", "Am", "pM", "Pm"]]


class DateTimeAlike(Feature):
    TYPE = "Datetime"

    @classmethod
    def is_datetime_valid(cls, **kwargs: Unpack[DatetimeDict]) -> Optional[DateTime]:
        raise NotImplementedError

    @staticmethod
    def _clean_groupdict(groupdict: dict[str, Optional[str]]) -> DatetimeDict:
        """Remove None values from a groupdict and return a DatetimeDict."""
        result = {}
        for k, v in groupdict.items():
            if v is None:
                continue
            key = k.rsplit("_", 1)[0]  # Split on last '_' and take first part
            if key in result:
                raise ValueError(f"Duplicate key found: {key}")
            result[key] = v
        return result

    @classmethod
    def match(cls, content: str) -> tuple[Optional[DatetimeDict], int]:
        """Finds the first match of a pattern in the content, returning the matched groups and the index of the last character in the match.

        If the pattern is not found, it returns None and zero.
        """
        if (match := cls.PATTERN.match(content)) and (
            groupdict := cls.validate(cls._clean_groupdict(match.groupdict()))
        ):
            return groupdict, match.end()
        return None, 0

    @classmethod
    def validate(cls, groupdict: DatetimeDict) -> Optional[DatetimeDict]:
        return groupdict

    @classmethod
    def fullmatch(cls, content: str) -> Optional[DatetimeDict]:
        """Fullmatch the content of a cell to the pattern of the class and return the match groups as a dictionary.

        It's useful for debugging and testing.
        """
        if (match := cls.PATTERN.fullmatch(content)) and (
            groupdict := cls.validate(cls._clean_groupdict(match.groupdict()))
        ):
            return groupdict

        return None

    @classmethod
    def evaluate(cls, s: str) -> bool:
        if (match := cls.fullmatch(s)) and cls.is_datetime_valid(**match):
            return True
        return False

    @classmethod
    def to_cell_number(cls, s: str) -> Optional[DateTime]:
        if (match := cls.fullmatch(s)) and (dt := cls.is_datetime_valid(**match)):
            return dt
        return None

    @classmethod
    def to_delta(
        cls, datetime: DateTime, base: Literal["1900", "1904"] = "1900"
    ) -> timedelta:
        match base:
            case "1900":
                return timedelta(days=datetime.days_since_1900())
            case "1904":
                return timedelta(days=datetime.days_since_1904())
            case _:
                raise ValueError(f"Invalid base year: {base}")

    @overload
    @classmethod
    def to_scalar_number(
        cls,
        delta: timedelta | str,
        num_per_day: int = 1,
    ) -> float | int:
        """Converts a timedelta object to a numeric representation."""

    @overload
    @classmethod
    def to_scalar_number(
        cls,
        dt: DateTime,
        base: Literal["1900"] | Literal["1904"] = "1900",
        number_per_day: int = 1,
    ) -> float | int:
        """Converts a datetime object to a numeric representation based on the configured base."""

    @classmethod
    def to_scalar_number(
        cls,
        value: timedelta | DateTime | str,
        base: Literal["1900"] | Literal["1904"] | int = "1900",
        number_per_day: int = 1,
    ) -> float | int:
        raise NotImplementedError

    @classmethod
    def to_datetime(
        cls,
        number: float,
        base: Literal["1900", "1904"] = "1900",
        number_per_day: int = 1,
    ) -> Optional[DateTime]:
        delta = DateTime.number_to_timedelta(number, number_per_day)
        base = (
            DateTime(1899, 12, 30, 0, 0, 0)
            if base == "1900"
            else DateTime(1904, 1, 1, 0, 0, 0)
        )
        return base + delta

    @staticmethod
    def convert_12hr_to_24hr(hour: int, apm: str) -> Optional[int]:
        if not (0 <= hour <= 12):
            return None

        if apm.lower() == "pm":
            return 12 if hour == 12 else hour + 12
        else:
            return 0 if hour == 12 else hour
