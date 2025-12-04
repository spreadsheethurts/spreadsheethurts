from .base import Formula


class Identity(Formula):
    """Represents the identity function."""

    def default(self, s: str) -> str:
        """Return the given cell."""
        return s

    def apply(self, strs: list[str]) -> str:
        """Return the first cell in the list."""
        return strs[0]

    @property
    def accept_index(self) -> bool:
        return False
