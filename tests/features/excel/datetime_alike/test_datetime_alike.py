from itertools import product

from wizard.features.excel.datetime_alike.time_alike import TimeAlike
from wizard.features.excel.datetime_alike.date_alike import DateAlike
from wizard.features.excel.datetime_alike.datetime_alike import IsDateTimeAlike


def test_datetime_examples():
    for date_scope, time_scope in product(
        DateAlike.__subclasses__(), TimeAlike.__subclasses__()
    ):
        for date, time in product(date_scope.EXAMPLES, time_scope.EXAMPLES):
            assert IsDateTimeAlike.evaluate(date + " " + time)
