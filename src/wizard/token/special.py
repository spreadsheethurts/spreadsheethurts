import string
from typing import Self, Generator

from wizard.token.base import Token


class Special(Token):
    """Represents a special sign (non-alphanumeric, non-space characters)."""

    SCOPE = list(string.punctuation)

    def __init__(self, token: str):
        assert (
            not token.isdigit()
            and not token.isalpha()
            and not token.isspace()
            and len(token) == 1
        )
        super().__init__(token)
        # if there are any special characters, add them to the scope
        if token not in self.SCOPE:
            self.SCOPE.append(token)

    def isspecial(self) -> bool:
        return True

    def transform(self) -> Generator[Self, None, None]:
        """Yield all possible punctuations."""
        for c in self.SCOPE:
            yield Special(c)

    @classmethod
    def specials(cls) -> list[Self]:
        """Return all special characters."""
        return [cls(c) for c in cls.SCOPE]
