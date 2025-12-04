from typing import Generator, Self

from wizard.token.base import Token


class Empty(Token):
    """Represents a empty token."""

    __slots__ = ()

    def __init__(self, *args, **kwargs): ...

    def isempty(self) -> bool:
        return True

    def __str__(self) -> str:
        return ""

    def transform(self) -> Generator[Self, None, None]:
        yield self

    def __len__(self) -> int:
        return 0
