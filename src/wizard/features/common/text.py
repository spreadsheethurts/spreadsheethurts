from wizard.feature import Feature
from wizard.typ.text import Text


class LeadingApostrophe(Feature):
    def evaluate(s: str) -> bool:
        return s.startswith("'")

    @classmethod
    def to_scalar_number(cls, s: str) -> Text:
        if s.startswith("'"):
            return Text(s[1:])
        return Text(s)

    @classmethod
    def to_cell_number(cls, s: str) -> Text:
        return cls.to_scalar_number(s)
