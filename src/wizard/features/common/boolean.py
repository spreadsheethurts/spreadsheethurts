from typing import Optional

from wizard.feature import Feature
from wizard.typ import Bool, Int


class Boolean(Feature):
    TYPE = "Bool"
    LOOKUP = {"true": True, "false": False}

    @classmethod
    def is_bool_valid(cls, s: str) -> Optional[Bool]:
        if (val := cls.LOOKUP.get(s.lower())) is not None:
            return Bool(val)
        return None

    @classmethod
    def evaluate(cls, s: str) -> bool:
        return cls.is_bool_valid(s) is not None

    @classmethod
    def to_scalar_number(cls, s: str) -> Optional[Int]:
        return Int(1) if cls.is_bool_valid(s) else Int(0)

    @classmethod
    def to_cell_number(cls, s: str) -> Optional[Bool]:
        return cls.is_bool_valid(s)
