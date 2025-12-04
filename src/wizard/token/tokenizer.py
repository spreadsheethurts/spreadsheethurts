import re

from .base import Token, Sequence
from .digit import Digit
from .alphabet import Alphabet
from .whitespace import Whitespace
from .special import Special


class Tokenizer:
    """Tokenizes a string."""

    token_patterns = [
        (r"\d+", Digit),
        (r"[a-zA-Z]+", Alphabet),
        (r"\s+", Whitespace),
        (r"[\W_]", Special),
    ]

    PATTERNS = "|".join(
        f"(?P<{cls.__qualname__}>{pattern})" for pattern, cls in token_patterns
    )

    def _generate_tokens(self, s: str) -> list[Token]:
        # m.lastgroup is the class name that the pattern matched with
        return [
            globals()[m.lastgroup](m.group()) for m in re.finditer(self.PATTERNS, s)
        ]

    def tokenize(self, s: str) -> Sequence[Token]:
        return Sequence(self._generate_tokens(s))

    __call__ = tokenize
