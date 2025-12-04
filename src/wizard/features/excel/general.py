from wizard.feature import GeneralFeature
from ..common.general import *
from ..common.pattern import Primitive

from wizard.typ import Text


class HasMonthName(GeneralFeature):
    MONTHS = {
        "january",
        "february",
        "march",
        "april",
        "may",
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
    }

    EXAMPLES = ["JanU", "Jan", "MaY"]

    @classmethod
    def evaluate(cls, s: str) -> bool:
        lower = s.lower()
        return any(
            full[:end] in lower
            for full in cls.MONTHS
            for end in range(3, len(full) + 1)
        )


class MaybeDateTime(GeneralFeature):
    EXAMPLES = ["5/1 12:", "Jan1 12:", "2021-1-1T12:"]

    @classmethod
    def might_be_triple_number_dates(cls, content: str) -> bool:
        sep = Primitive.slash() | Primitive.hyphen()
        pattern = (
            (Primitive.digits() + sep + Primitive.digits() + sep + Primitive.digits())
            .join_with_tail(Primitive.anyspace())
            .compile()
        )
        return pattern.search(content) is not None

    @classmethod
    def might_be_double_number_dates(cls, content: str) -> bool:
        sep = Primitive.slash() | Primitive.hyphen()
        pattern = (
            (Primitive.digits() + sep + Primitive.digits())
            .join_with_tail(Primitive.anyspace())
            .compile()
        )
        return pattern.search(content) is not None

    @classmethod
    def evaluate(cls, s: str) -> bool:
        if ":" not in s:
            return False

        if (
            HasMonthName.evaluate(s)
            or cls.might_be_triple_number_dates(s)
            or cls.might_be_double_number_dates(s)
        ):
            return True

        return False


class MaybeSymbolicNumber(GeneralFeature):
    """Feature identifying strings that might represent symbolic numeric formats such as currency, percentage, or scientific notation."""

    EXAMPLES = ["123.45e-1", "$123.45", "123.45%"]
    MAYBE_EXPONENT = re.compile(r"(?<![a-zA-Z])[eE][\+\-]?\d+")

    @classmethod
    def evaluate(cls, s: str) -> bool:
        if cls.MAYBE_EXPONENT.search(s):
            return True

        for sym in ("$", "%", "¥", "€"):
            if sym in s:
                return True
        return False


class ContainsTab(GeneralFeature):
    """WORKAROUND: The TextToColumns method exhibits unexpected behavior by defaulting to a tab delimiter, even when tab is set to False."""

    EXAMPLES = ["Higashimori\t , M., Dr."]

    @classmethod
    def evaluate(cls, s: str) -> bool:
        return "\t" in s

    @classmethod
    def to_cell_number(cls, s: str) -> Text:
        return Text(s.split("\t")[0])

    @classmethod
    def to_scalar_number(cls, s: str) -> Text:
        return Text(s.split("\t")[0])
