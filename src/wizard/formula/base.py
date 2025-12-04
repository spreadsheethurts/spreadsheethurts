from abc import ABC, abstractmethod


class Formula(ABC):

    @abstractmethod
    def default(self, arg: str | tuple[int, int]) -> str: ...

    @abstractmethod
    def apply(self, cells: list[str]) -> str: ...

    @property
    @abstractmethod
    def accept_index(self) -> bool: ...
