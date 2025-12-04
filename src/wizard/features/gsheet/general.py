from wizard.feature import GeneralFeature
from ..common.general import *
from ..common.pattern import Primitive


class IsTooLong(GeneralFeature):
    """Feature that identifies strings that are too long(longer than 309 characters)."""

    EXAMPLES = ["a" * 310]
    TYPE = "Text"

    @classmethod
    def evaluate(cls, s: str) -> bool:
        return len(s) > 309


class MaybeDateTime(GeneralFeature):
    """Feature identifying strings that might represent datetime formats."""

    EXAMPLES = ["1/1 12:1", "1,1 12 1:10", "Jan1 1:", "4-19 11pm"]
    COUNTER_EXAMPLES = ["12:1 1/1"]

    @classmethod
    def evaluate(cls, s: str) -> bool:
        lower = s.lower()

        if ":" in s:
            index = s.index(":")
        elif apm := re.search(r"[aApP][mM]", s):
            index = apm.start()
        else:
            return False

        # 1. ISO 8601 format
        if "T" in s and s.index("T") < index:
            return True

        # 2. Month name
        for month in HasMonthName.MONTHS:
            if month in lower:
                return True

        # 3. `DIGIT-SEP-DIGIT` pattern followed by a colon, where SEP is one of the following:
        # slash, hyphen, somespace, anyspace + dot + somespace, comma + anyspace
        sep = (
            Primitive.slash()
            | Primitive.hyphen()
            | Primitive.somespace()
            | (Primitive.anyspace() + Primitive.dot() + Primitive.somespace()).group()
            | (Primitive.comma() + Primitive.anyspace()).group()
        ).group()
        pattern = (Primitive.digits() + sep + Primitive.digits()).compile()
        if pattern.search(s, endpos=index):
            return True

        return False