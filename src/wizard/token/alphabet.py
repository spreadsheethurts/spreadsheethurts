import string
from typing import Generator, Self, Optional
from pathlib import Path

from wizard.token.base import Token


WORDS: Optional[list[str]] = None

if WORDS is None:
    path = Path(__file__).parent.parent / "assets/wordlists.txt"
    with open(path) as f:
        WORDS = list(map(lambda x: x.rstrip(), f.readlines()))


class Alphabet(Token):
    """Represents a string."""

    SCOPE = list(string.ascii_letters)

    def __init__(self, letters: str):
        assert letters.isalpha(), f"Invalid letters: {letters}"
        super().__init__(letters)

    def isalphabet(self) -> bool:
        return True

    def transform(self) -> Generator[Self, None, None]:
        yield from self.prefixes()
        yield from self.suffixes()
        yield from self.common_operations()

    @classmethod
    def factory(cls) -> Self: ...

    def prefixes(self) -> Generator[Self, None, None]:
        """Generate all prefixes of the string, ranging in length from one to the full length of the string itself."""
        for i in range(1, len(self.value) + 1):
            yield Alphabet(self.value[:i])

    def suffixes(self) -> Generator[Self, None, None]:
        """Generate all suffixes of the string, ranging in length from one to the full length of the string itself."""
        for i in range(1, len(self.value) + 1):
            yield Alphabet(self.value[-i:])

    def common_operations(self) -> Generator[Self, None, None]:
        yield Alphabet(self.value.capitalize())
        yield Alphabet(self.value.lower())
        yield Alphabet(self.value.upper())
