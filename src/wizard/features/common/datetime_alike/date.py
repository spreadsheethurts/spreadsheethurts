from typing import Optional, TypedDict


class DateDict(TypedDict):
    year: Optional[str | int]
    month: Optional[str | int]
    day: Optional[str | int]
    day_of_week: Optional[str]
