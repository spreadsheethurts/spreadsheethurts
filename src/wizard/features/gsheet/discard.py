import re
from wizard.feature import DiscardFeature
from .num_alike import CURRENCY_SYMBOL_EXAMPLE, PERCENT_SYMBOL


class MightBeFormula(DiscardFeature):
    # Case 1: Match strings that start with a sign (+, - or =).
    # Case 2: Match signed time strings.
    EXAMPLES = [" + 22/333.33", "+22/333.33", "1-1156 -34: 12"]
    PATTERN = re.compile(r"(\s*[-+=]\s*.*)|(.*(?:-\d+:|:-\d+).*)")

    @classmethod
    def evaluate(cls, s: str) -> bool:
        return cls.PATTERN.match(s) is not None


class MightBePercentageCurrency(DiscardFeature):

    @classmethod
    def evaluate(cls, s: str) -> bool:
        return CURRENCY_SYMBOL_EXAMPLE in s or PERCENT_SYMBOL.regex in s
