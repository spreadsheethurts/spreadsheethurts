from typing import Optional

from wizard.feature import WeirdFeature
from ..common.pattern import Primitive
from wizard.typ import Float


class ColonWithLeadingSpace(WeirdFeature):
    EXAMPLES = [" : ", " :"]

    PATTERN = (
        Primitive.somespace() + Primitive.colon() + Primitive.anyspace()
    ).compile()

    @classmethod
    def evaluate(cls, s: str) -> bool:
        return cls.PATTERN.fullmatch(s) is not None

    @classmethod
    def to_cell_number(cls, s: str) -> Optional[Float]:
        if cls.evaluate(s):
            return Float(-417.6666666666667)
        return None

    @classmethod
    def to_scalar_number(cls, s: str) -> Optional[Float]:
        if cls.evaluate(s):
            return Float(-417.6666666666667)
        return None
