from wizard.feature import DiscardFeature


class Error(DiscardFeature):

    @classmethod
    def evaluate(cls, s: str) -> bool:
        codes = ["#NULL!", "#DIV/0!", "#VALUE!", "#REF!", "#NAME?", "#NUM!", "#N/A"]
        return s in codes
