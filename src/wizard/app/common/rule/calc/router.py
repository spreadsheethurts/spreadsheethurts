from ..decisions import AutoNextStrEnum
from wizard.features.calc import *


class LettersDigitsRouterType(AutoNextStrEnum):
    MD = "MD"
    MY = "MY"


class LettersDigitsRouterFeature:

    @classmethod
    def evaluate(cls, s: str) -> LettersDigitsRouterType:
        if match := re.search("\d+", s):
            digits = match.group()
            if len(digits) <= 2 and 0 < int(digits) <= 31:
                return LettersDigitsRouterType.MD

        return LettersDigitsRouterType.MY


class SymbolicNumberRouterType(AutoNextStrEnum):
    CURRENCY = "CURRENCY"
    PERCENTAGE = "PERCENTAGE"
    SCIENTIFIC = "SCIENTIFIC"


class SymbolicNumberRouterFeature:

    @classmethod
    def evaluate(cls, s: str) -> SymbolicNumberRouterType:
        if "e" in s or "E" in s:
            return SymbolicNumberRouterType.SCIENTIFIC
        elif "%" in s:
            return SymbolicNumberRouterType.PERCENTAGE
        elif "$" in s:
            return SymbolicNumberRouterType.CURRENCY
        return SymbolicNumberRouterType.NEXT


class DigitsLettersDigitsRouterType(AutoNextStrEnum):
    DMY = "DMY"
    YMD = "YMD"


class DigitsLettersDigitsRouterFeature:
    @classmethod
    def evaluate(cls, s: str) -> DigitsLettersDigitsRouterType:
        if (first_digits := re.search("\d+", s)) and (
            first_letters := re.search("[a-zA-Z]+", s)
        ):
            first_digits, first_letters = first_digits.group(), first_letters.group()
            if utils.get_day(first_digits) and utils.get_month(first_letters):
                return DigitsLettersDigitsRouterType.DMY
        return DigitsLettersDigitsRouterType.YMD


class MaybeISO8601DateTimeType(AutoNextStrEnum):
    ISO8601 = "ISO8601"


class MaybeISO8601DateTime:
    @classmethod
    def evaluate(cls, s: str) -> MaybeISO8601DateTimeType:
        colon_index = s.index(":")
        if "T" in s and s.index("T") < colon_index:
            return MaybeISO8601DateTimeType.ISO8601

        return MaybeISO8601DateTimeType.NEXT


class HMSorMSMType(AutoNextStrEnum):
    HMS = "HMS"
    MSM = "MSM"


class HMSorMSM:
    @classmethod
    def evaluate(cls, s: str) -> HMSorMSMType:
        msms = [
            MinuteSecondMicrosecond,
            MinuteSecondMicrosecondNegative,
            MSMWithSpaceAsFirstSep,
        ]
        hmss = [
            HourMinuteSecond,
            HourMinuteSecondSpecial,
            HMSDot,
            HMSWithSpaceAsFirstSep,
            HMSWithSpaceAsFirstSepWithAdditionalSuffix,
        ]

        for msm in msms:
            if msm.evaluate(s):
                return HMSorMSMType.MSM
        for hms in hmss:
            if hms.evaluate(s):
                return HMSorMSMType.HMS

        return HMSorMSMType.MSM
