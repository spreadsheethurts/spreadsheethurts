import re
from ..decisions import AutoNextStrEnum
from wizard.features.gsheet import *


class SymbolicNumberRouterType(AutoNextStrEnum):
    CURRENCY = "CURRENCY"
    PERCENTAGE = "PERCENTAGE"
    SCIENTIFIC = "SCIENTIFIC"


class SymbolicNumberRouter:
    @classmethod
    def evaluate(cls, s: str) -> SymbolicNumberRouterType:
        if "e" in s or "E" in s:
            return SymbolicNumberRouterType.SCIENTIFIC

        if "%" in s:
            return SymbolicNumberRouterType.PERCENTAGE

        for sym in ("$", "€"):
            if sym in s:
                return SymbolicNumberRouterType.CURRENCY
        return SymbolicNumberRouterType.SCIENTIFIC


class LettersDigitsRouterType(AutoNextStrEnum):
    MD = "MD"
    MY = "MY"


class LettersDigitsRouter:
    @classmethod
    def evaluate(cls, s: str) -> LettersDigitsRouterType:
        if digits := re.search("\d+", s):
            digits = digits.group()
            if len(digits) <= 2:
                return LettersDigitsRouterType.MD

        return LettersDigitsRouterType.MY


class DigitsLettersRouterType(AutoNextStrEnum):
    DM = "DM"
    YM = "YM"


class DigitsLettersRouter:
    @classmethod
    def evaluate(cls, s: str) -> DigitsLettersRouterType:
        if digits := re.search("\d+", s):
            digits = digits.group()
            if len(digits) <= 2:
                return DigitsLettersRouterType.DM

        return DigitsLettersRouterType.YM


class DoubleDigitsRouterType(AutoNextStrEnum):
    MD = "MD"
    MY = "MY"
    YM = "YM"


class DoubleDigitsRouter:
    @classmethod
    def evaluate(cls, s: str) -> DoubleDigitsRouterType:
        if (comps := re.findall("\d+", s)) and len(comps) == 2:
            first_digits, second_digits = comps[0], comps[1]
            if len(first_digits) <= 2 and len(second_digits) <= 2:
                return DoubleDigitsRouterType.MD
            elif len(first_digits) <= 2 and len(second_digits) == 4:
                return DoubleDigitsRouterType.MY

        return DoubleDigitsRouterType.YM
