from wizard.feature import DiscardFeature
from wizard.features.common.pattern import String
from ..common.error import Error  # noqa


class MightBeFormula(DiscardFeature):
    EXAMPLES = ["-1", "12:34 - am", "12:34 + am", "12:32 -", "333-:"]
    PATTERN = (
        "^[-+=].*"
        | (".*" + ("[-+]" + String.apm()).join_both_ends(String.anyspace())).group()
        | (".*" + String.anyspace() + "[-+]" + String.anyspace()).group()
        | ".*\(.*\).*"
        | ".*-.*:.*"
        | ".*:.*-.*"
    ).compile()

    @classmethod
    def evaluate(cls, s: str) -> bool:
        return cls.PATTERN.fullmatch(s) is not None
