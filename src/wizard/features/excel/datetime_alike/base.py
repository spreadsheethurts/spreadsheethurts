from datetime import timedelta
from typing import Optional, Literal

from ...common.datetime_alike import (
    DateTimeAlike as GeneralDatetimeAlike,
    DatetimeDict,
    DateDict,
    TimeDict,
)
from wizard.typ import ExcelDateTime


class ExcelDateTimeAlikeBase(GeneralDatetimeAlike):

    @classmethod
    def to_scalar_number(
        cls,
        value: timedelta | ExcelDateTime | str,
        base: Literal["1900"] | Literal["1904"] | int = "1900",
        number_per_day: int = 1,
    ) -> Optional[float | int]:
        if isinstance(value, str):
            if (match := cls.fullmatch(value)) and (
                dt := cls.is_datetime_valid(**match)
            ):
                return cls.to_scalar_number(dt, base, number_per_day)
        elif isinstance(value, timedelta):
            return ExcelDateTime.timedelta_to_number(value, number_per_day)
        elif isinstance(value, ExcelDateTime):
            return (
                value.days_since_1900() * number_per_day
                if base == "1900"
                else value.days_since_1904() * number_per_day
            )
        return None

    @classmethod
    def to_datetime(
        cls,
        number: float | int,
        base: Literal["1900"] | Literal["1904"] = "1900",
        number_per_day: int = 1,
    ) -> Optional[ExcelDateTime]:
        delta = ExcelDateTime.number_to_timedelta(number, number_per_day)
        base = (
            ExcelDateTime(1900, 1, 1, 0, 0, 0)
            if base == "1900"
            else ExcelDateTime(1904, 1, 1, 0, 0, 0)
        )
        return base + delta - timedelta(days=1)
