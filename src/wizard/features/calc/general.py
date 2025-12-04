from wizard.feature import GeneralFeature
from ..common.general import *


class IsTooLong(GeneralFeature):
    """Feature that identifies strings that are too long(longer than 308 characters)."""

    EXAMPLES = ["a" * 309]
    TYPE = "Text"

    @classmethod
    def evaluate(cls, s: str) -> bool:
        return len(s) > 308


class MaybeDateTime(GeneralFeature):
    """Feature identifying strings that might represent datetime formats."""

    EXAMPLES = ["5/1 12:", "Jan1 12:", "2021-1-1T12:"]

    @classmethod
    def evaluate(cls, s: str) -> bool:
        if ":" not in s:
            return False

        colon_index = s.index(":")
        # 1. ISO 8601 format
        if "T" in s and s.index("T") < colon_index:
            return True

        # 2. Month name + colon
        lower_s = s.lower()
        for month in HasMonthName.MONTHS:
            if month in lower_s and lower_s.index(month) < colon_index:
                return True

        # 3. Digit followed by / or -, then colon
        for i in range(colon_index):
            if (
                s[i].isdigit()
                and i + 1 < len(s)
                and (s[i + 1] == "/" or s[i + 1] == "-")
            ):
                return True

        return False


class MaybeSymbolicNumber(GeneralFeature):
    """Feature identifying strings that might represent symbolic numeric formats such as currency, percentage, or scientific notation."""

    EXAMPLES = ["123.45e-1", "$123.45", "123.45%", "2 e 1"]
    MAYBE_EXPONENT = re.compile(r"(?<![a-zA-Z])[eE] *[\+\-]? *\d+")

    @classmethod
    def evaluate(cls, s: str) -> bool:
        if cls.MAYBE_EXPONENT.search(s):
            return True

        for sym in ("$", "%"):
            if sym in s:
                return True
        return False
