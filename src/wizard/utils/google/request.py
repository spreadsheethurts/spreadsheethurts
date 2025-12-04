from typing import Optional, Mapping, Any, Literal, Dict
from enum import StrEnum

from wizard.base import Serializable

JsonDict = Dict


class RequestParam(Serializable):
    method: Literal["get", "post", "put", "delete"]
    url: str
    params: Optional[Mapping[str, Any]] = None
    body: Optional[Mapping[str, Any]] = None
    data: Optional[bytes] = None
    headers: Optional[Mapping[str, str]] = None


class ValueInputOption(StrEnum):
    raw = "RAW"
    user_entered = "USER_ENTERED"


class ValueRenderOption(StrEnum):
    formatted = "FORMATTED_VALUE"
    unformatted = "UNFORMATTED_VALUE"
    formula = "FORMULA"


class DateTimeOption(StrEnum):
    serial_number = "SERIAL_NUMBER"
    formatted_string = "FORMATTED_STRING"


class QuotaExceeded(Exception):
    pass


class APIError(Exception):
    def __init__(self, error: JsonDict):
        super().__init__(error)
