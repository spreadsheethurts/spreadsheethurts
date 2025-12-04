from itertools import product

from wizard.features.excel.datetime_alike.time_alike import (
    HourMinute,
    MinuteSecondMicrosecond,
    HourMinuteSecond,
    HourMinuteSecondMicrosecond,
    WeirdHourDecimalMinuteInteger,
)
from wizard.features.excel.datetime_alike.date_alike import DateAlike
from wizard.features.excel.datetime_alike.timedate_alike import IsTimeDateAlike


def test_timedate_examples():
    time_scopes = [
        HourMinute,
        MinuteSecondMicrosecond,
        HourMinuteSecond,
        HourMinuteSecondMicrosecond,
        WeirdHourDecimalMinuteInteger,
    ]
    for date_scope, time_scope in product(DateAlike.__subclasses__(), time_scopes):
        for date, time in product(date_scope.EXAMPLES, time_scope.EXAMPLES):
            assert IsTimeDateAlike.evaluate(time + " " + date)
