import re

from wizard.feature import DiscardFeature
from wizard.utils import find_leaf_classes
from .datetime_alike.date_alike import DateAlike
from .datetime_alike.time_alike import TimeAlike
from ..common.error import Error  # noqa


class DateConfusedTime(DiscardFeature):
    """
    "June 2021 12:34-56-"
    "1 June 888:56/22"
    """

    DATESCOPES: list[DateAlike] = list(find_leaf_classes(DateAlike).values())
    TIMESCOPES: list[TimeAlike] = list(find_leaf_classes(TimeAlike).values())

    @classmethod
    def evaluate(cls, s: str) -> bool:
        for date_cls in cls.DATESCOPES:
            date_match, date_remainder_idx = date_cls.match(s)
            if date_match and date_cls.is_datetime_valid(**date_match):
                # Ensure the remainder starts with a space to confirm the time is not part of the date.
                # Pattern matching in the date consumes the ending space, so we need to check the char-
                # acter before the remainder.
                if s[date_remainder_idx - 1] == " ":
                    remainder = s[date_remainder_idx:]
                    for time_cls in cls.TIMESCOPES:
                        time_match, time_remainder_idx = time_cls.match(remainder)
                        if time_match and time_cls.is_datetime_valid(**time_match):
                            # something left, e.g. "Jun1 22:11/11"
                            if time_remainder_idx != len(s):
                                return True
        return False


class MightBeFormula(DiscardFeature):
    PATTERN = re.compile(r"^[\-\+=]")

    @classmethod
    def evaluate(cls, s: str) -> bool:
        return cls.PATTERN.match(s) is not None
