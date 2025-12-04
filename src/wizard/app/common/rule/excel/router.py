from ..decisions import AutoNextStrEnum
from wizard.features.excel import *


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

        for sym in ("$", "¥", "€"):
            if sym in s:
                return SymbolicNumberRouterType.CURRENCY

        return SymbolicNumberRouterType.SCIENTIFIC


class DoubleDigitsRouterType(AutoNextStrEnum):
    MD = "MD"
    DM = "DM"
    YM = "YM"


class DoubleDigitsRouter:
    @classmethod
    def evaluate(cls, s: str) -> DoubleDigitsRouterType:
        if MonthNumberDay.evaluate(s):
            return DoubleDigitsRouterType.MD
        elif DayMonthNumber.evaluate(s):
            return DoubleDigitsRouterType.DM
        return DoubleDigitsRouterType.YM


class LetterDigitsRouterType(AutoNextStrEnum):
    MD = "MD"
    MY = "MY"


class LetterDigitsRouter:
    @classmethod
    def evaluate(cls, s: str) -> LetterDigitsRouterType:
        if digits := re.search("\d+", s):
            digits = digits.group()
            if len(digits) <= 2 and 0 < int(digits) <= 31:
                return LetterDigitsRouterType.MD
        return LetterDigitsRouterType.MY


class HMSorMSMType(AutoNextStrEnum):
    HMS = "HMS"
    MSM = "MSM"


class HMSorMSM:
    @classmethod
    def evaluate(cls, s: str) -> HMSorMSMType:
        msms = [
            MinuteSecondMicrosecond,
            MinuteSecondMicrosecondSpecial,
        ]

        hmss = [
            HourMinuteSecond,
            HourMinuteSecondSpecial,
        ]

        for msm in msms:
            if msm.evaluate(s):
                return HMSorMSMType.MSM
        for hms in hmss:
            if hms.evaluate(s):
                return HMSorMSMType.HMS

        return HMSorMSMType.MSM
