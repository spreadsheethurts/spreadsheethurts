from wizard.typ.datetime.gregoriandatetime import GregorianDateTime
from typing import Any, Literal
import datetime
import re

VALID_PYTHON_TYPES = (
    float
    | int
    | str
    | datetime.date
    | datetime.time
    | datetime.timedelta
    | datetime.datetime
    | bool
    | GregorianDateTime
)

VALID_EZODF_TYPES = Literal["float", "int", "string", "date", "time", "boolean"]


PYTHON_TYPE2EZODF_TYPE = {
    float: "float",
    int: "float",
    str: "string",
    datetime.date: "date",
    datetime.time: "time",
    datetime.timedelta: "timedelta",
    datetime.datetime: "datetime",
    GregorianDateTime: "gregoriandatetime",
    bool: "boolean",
}


def resolve_ezodf_to_python(v, type) -> Any:
    """Ezodf handles date and time values as strings; this function converts them to their correct types."""
    if type == "date":
        return _date_value(v)
    elif type == "time":
        return _time_value(v)
    return v


def resolve_python_to_ezodf(
    value: VALID_PYTHON_TYPES,
) -> tuple[VALID_PYTHON_TYPES, VALID_EZODF_TYPES]:
    value_type = PYTHON_TYPE2EZODF_TYPE[type(value)]
    if value_type == "time":
        value = value.strftime("PT%HH%MM%SS")
    elif value_type == "timedelta":
        hours = value.days * 24 + value.seconds // 3600
        minutes = (value.seconds // 60) % 60
        seconds = value.seconds % 60
        value = "PT%02dH%02dM%02dS" % (hours, minutes, seconds)
        value_type = "time"
    elif value_type == "datetime" or value_type == "gregoriandatetime":
        value = "%d-%02d-%02dT%02d:%02d:%02d" % (
            value.year,
            value.month,
            value.day,
            value.hour,
            value.minute,
            value.second,
        )
        value_type = "date"
    elif value_type == "date":
        value = value.strftime("%Y-%m-%d")
    return value, value_type


# The following code is from pyexcel_ods3
def _date_value(value):
    """convert to data value accroding ods specification"""
    ret = "invalid"
    try:
        # catch strptime exceptions only
        # four or five digit years are supported
        if len(value) == 10 or len(value) == 11:
            ret = GregorianDateTime.strptime(value, "%Y-%m-%d")
        elif len(value) == 19:
            ret = GregorianDateTime.strptime(value, "%Y-%m-%dT%H:%M:%S")
        elif len(value) > 19:
            ret = GregorianDateTime.strptime(value[0:26], "%Y-%m-%dT%H:%M:%S.%f")
    except ValueError:
        pass
    if ret == "invalid":
        raise Exception("Bad date value %s" % value)

    return ret


def _time_value(value):
    """convert to time value accroding the specification"""

    results = re.match(r"PT(\d+)H(\d+)M(\d+)S", value)
    if results and len(results.groups()) == 3:
        hour = int(results.group(1))
        minute = int(results.group(2))
        second = int(results.group(3))
        if hour < 24:
            ret = datetime.time(hour, minute, second)
        else:
            ret = datetime.timedelta(hours=hour, minutes=minute, seconds=second)
    else:
        ret = None
    return ret
