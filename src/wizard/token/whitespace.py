import string
from typing import Self, Generator
import random

from wizard.token.base import Token


class Whitespace(Token):
    """Represents a space or any other whitespace character."""

    SCOPE = list(string.whitespace)

    def __init__(self, spaces: str):
        assert spaces.isspace(), f"Invalid spaces: {spaces}"
        super().__init__(spaces)

    def iswhitespace(self) -> bool:
        return True

    def transform(self) -> Generator[Self, None, None]:
        """Generate strings of spaces, each with an incrementally increasing number of leading spaces."""
        for num in range(1, random.randint(2, 20)):
            yield Whitespace(" " * num + self.value)

    def decrease(self) -> Self:
        """Decrease the number of spaces in the string by one."""
        if len(self.value) == 1:
            return self
        return Whitespace(self.value[1:])

    def decrease_by(self, num: int) -> Self:
        """Decrease the number of spaces in the string by a given number."""
        if num >= len(self.value):
            return Whitespace(" ")
        return Whitespace(self.value[num:])

    def increase_by(self, num: int) -> Self:
        """Increase the number of spaces in the string by a given number."""
        return Whitespace(" " * num + self.value)

    def increase(self) -> Self:
        """Increase the number of spaces in the string by one."""
        return Whitespace(" " + self.value)

    @classmethod
    def space(cls, n: int) -> Self:
        return Whitespace(" " * n)
