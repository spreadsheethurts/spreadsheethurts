from typing import Optional, TypedDict, Literal


class TimeDict(TypedDict):
    hour: Optional[str | int]
    minute: Optional[str | int]
    second: Optional[str | int]
    microsecond: Optional[str | int]
    apm: Optional[Literal["am", "pm", "AM", "PM", "aM", "Am", "pM", "Pm"]]
