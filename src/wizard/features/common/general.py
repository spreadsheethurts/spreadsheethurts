import re
from wizard.feature import GeneralFeature


class HasMonthName(GeneralFeature):
    """Feature that identifies potential datetime strings containing a month name."""

    MONTHS = {
        "january",
        "jan",
        "february",
        "feb",
        "march",
        "mar",
        "april",
        "apr",
        "may",
        "june",
        "jun",
        "july",
        "jul",
        "august",
        "aug",
        "september",
        "sep",
        "october",
        "oct",
        "november",
        "nov",
        "december",
        "dec",
    }

    @classmethod
    def evaluate(cls, s: str) -> bool:
        lower = s.lower()
        return any(month in lower for month in cls.MONTHS)


class IsTooLong(GeneralFeature):
    """Feature that identifies strings that are too long(longer than 308 characters)."""

    EXAMPLES = ["a" * 309]
    TYPE = "Text"

    @classmethod
    def evaluate(cls, s: str) -> bool:
        return len(s) > 308


class HasDigits(GeneralFeature):
    """Feature that identifies strings with digits, a necessary condition for potential numeric strings."""

    @classmethod
    def evaluate(cls, s: str) -> bool:
        return any(char.isdigit() for char in s)


def count_digits_parts(s: str) -> int:
    """Counts the number of continuous digit parts in a string."""
    count = 0
    in_group = False

    for c in s:
        if c.isdigit():
            if not in_group:
                count += 1
                in_group = True
        else:
            in_group = False

    return count


class HasOneDigitsGroup(GeneralFeature):
    """Feature that identifies strings with exactly one digit group."""

    EXAMPLES = ["1234567890", "Jan1", "$1", "1%"]

    @classmethod
    def evaluate(cls, s: str) -> bool:
        return count_digits_parts(s) == 1


class HasTwoDigitsGroups(GeneralFeature):
    """Feature that identifies strings with exactly two digit groups."""

    EXAMPLES = ["1-1", "1-Jan-2021", "1145.14"]

    @classmethod
    def evaluate(cls, s: str) -> bool:
        return count_digits_parts(s) == 2


class HasThreeDigitsGroups(GeneralFeature):
    """Feature that identifies strings with exactly three digit groups."""

    EXAMPLES = ["1-1-1", "1145.14e-1", "1 1/2"]

    @classmethod
    def evaluate(cls, s: str) -> bool:
        return count_digits_parts(s) == 3


class HasFourDigitsGroups(GeneralFeature):
    """Feature that identifies strings with exactly four digit groups."""

    EXAMPLES = ["12:34:56.789"]

    @classmethod
    def evaluate(cls, s: str) -> bool:
        return count_digits_parts(s) == 4


class MaybeSymbolicNumber(GeneralFeature):
    """Feature identifying strings that might represent symbolic numeric formats such as currency, percentage, or scientific notation."""

    EXAMPLES = ["123.45e-1", "$123.45", "123.45%"]
    MAYBE_EXPONENT = re.compile(r"(?<![a-zA-Z])[eE][\+\-]?\d+")

    @classmethod
    def evaluate(cls, s: str) -> bool:
        if cls.MAYBE_EXPONENT.search(s):
            return True

        for sym in ("$", "%"):
            if sym in s:
                return True
        return False


class MaybeTime(GeneralFeature):
    """Feature that identifies strings that might be times."""

    EXAMPLES = ["12:34", "12:34:56", "12:34 am", "12:34 pm"]

    @classmethod
    def evaluate(cls, s: str) -> bool:
        lower = s.lower()
        return any(sym in lower for sym in [":", "am", "pm"])
