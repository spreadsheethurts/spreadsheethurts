from datetime import timedelta
from typing import Literal, Optional, overload
from ...common.datetime_alike import (
    DateTimeAlike as GeneralDateTimeAlike,
    DatetimeDict,  # noqa: F401
    DateDict,  # noqa: F401
    TimeDict,  # noqa: F401
)
from wizard.typ import GregorianDateTime, Int, Float


class CalcDateTimeAlikeBase(GeneralDateTimeAlike):

    @overload
    @classmethod
    def to_scalar_number(
        cls,
        delta: timedelta,
        num_per_day: int = 1,
    ) -> Int | Float:
        """Converts a timedelta object to a numeric representation."""

    @overload
    @classmethod
    def to_scalar_number(
        cls,
        dt: GregorianDateTime,
        base: Literal["1900"] | Literal["1904"] = "1900",
        number_per_day: int = 1,
    ) -> Int | Float:
        """Converts a datetime object to a numeric representation based on the configured base."""

    @classmethod
    def to_scalar_number(
        cls,
        value: timedelta | GregorianDateTime | str,
        base: Literal["1900"] | Literal["1904"] | int = "1900",
        number_per_day: int = 1,
    ) -> Int | Float:
        if isinstance(value, str):
            if (match := cls.fullmatch(value)) and (
                dt := cls.is_datetime_valid(**match)
            ):
                return cls.to_scalar_number(dt, base, number_per_day)
        elif isinstance(value, timedelta):
            return GregorianDateTime.timedelta_to_number(value, number_per_day)
        elif isinstance(value, GregorianDateTime):
            return (
                value.days_since_1900() * number_per_day
                if base == "1900"
                else value.days_since_1904() * number_per_day
            )

    @classmethod
    def to_datetime(
        cls,
        number: float,
        base: Literal["1900", "1904"] = "1900",
        number_per_day: int = 1,
    ) -> Optional[GregorianDateTime]:
        delta = GregorianDateTime.number_to_timedelta(number, number_per_day)
        base = (
            GregorianDateTime(1899, 12, 30, 0, 0, 0)
            if base == "1900"
            else GregorianDateTime(1904, 1, 1, 0, 0, 0)
        )
        return base + delta
