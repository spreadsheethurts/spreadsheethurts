from abc import ABC, abstractmethod
from typing import Generator, Self, Generic, TypeVar, Iterable, Callable, overload

from functional.pipeline import Sequence as _Sequence
from functional.transformations import Transformation


T = TypeVar("T")


class Token(ABC):
    """Base class for all tokens."""

    __match_args__ = ("value",)
    __slots__ = ("value",)

    def __init__(self, value: str) -> None:
        self.value = value

    def isdigit(self) -> bool:
        return False

    def isalphabet(self) -> bool:
        return False

    def isspecial(self) -> bool:
        return False

    def iswhitespace(self) -> bool:
        return False

    def isempty(self) -> bool:
        return False

    @abstractmethod
    def transform(self) -> Generator[Self, None, None]:
        """Apply transformation on the token."""
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.value})"

    def __str__(self) -> str:
        return self.value

    def __len__(self) -> int:
        return len(self.value)

    def __eq__(self, value: object) -> bool:
        if isinstance(value, Token):
            return self.value == value.value
        return super().__eq__(value)


def sequence_wrapper(func: callable):
    """Changes the return type of a function to TokenStream if it returns a Sequence."""

    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if isinstance(result, _Sequence):
            return Sequence(result)
        return result

    return wrapper


class Sequence(Generic[T], _Sequence):
    def __init__(self, data: Iterable[T]):
        super().__init__(data, max_repr_items=10)

    def __str__(self):
        return self.make_string("")

    def __getattribute__(self, __name: str):
        """Wraps all methods to ensure they return a Sequence."""
        attribute = super().__getattribute__(__name)
        if callable(attribute):
            return sequence_wrapper(attribute)
        return attribute

    def append(self, token: T) -> Self:

        def _append(it: Self, token: T):
            for i in it:
                yield i
            yield token

        return self._transform(
            Transformation("append", lambda sequence: _append(sequence, token), None)
        )

    @overload
    def replace(self, index: int, token: T) -> Self:
        """Replace the token at the given index with the new token."""

    @overload
    def replace(self, predicate: Callable[[T], bool], token: T) -> Self:
        """Replace the first token that satisfies the predicate with the new token."""

    def replace(self, index_or_predicate: int | Callable[[T], bool], token: T) -> Self:
        def _replace(it: Self, index_or_predicate: int | Callable[[T], bool], token: T):
            replaced = False
            for i, t in enumerate(it):
                if replaced:
                    yield t
                else:
                    if isinstance(index_or_predicate, int):
                        if i == index_or_predicate:
                            yield token
                            replaced = True
                        else:
                            yield t
                    else:
                        if index_or_predicate(t):
                            yield token
                            replaced = True
                        else:
                            yield t

        return self._transform(
            Transformation(
                "replace",
                lambda sequence: _replace(sequence, index_or_predicate, token),
                None,
            )
        )

    @overload
    def insert(self, index: int, token: T) -> Self:
        """Insert the token at the given index."""

    @overload
    def insert(
        self, predicate: Callable[[T], bool], token: T, before: bool = True
    ) -> Self:
        """Insert the token before(after) the first token that satisfies the predicate."""

    def insert(
        self,
        index_or_predicate: int | Callable[[T], bool],
        token: T,
        before: bool = True,
    ) -> Self:
        def _insert(it: Self, index_or_predicate: int | Callable[[T], bool], token: T):
            inserted = False
            for i, t in enumerate(it):
                if inserted:
                    yield t
                else:
                    if isinstance(index_or_predicate, int):
                        if i == index_or_predicate:
                            if before:
                                yield token
                                yield t
                            else:
                                yield t
                                yield token
                            inserted = True
                        else:
                            yield t
                    else:
                        if index_or_predicate(t):
                            if before:
                                yield token
                                yield t
                            else:
                                yield t
                                yield token
                            inserted = True
                        else:
                            yield t

        return self._transform(
            Transformation(
                "insert",
                lambda sequence: _insert(sequence, index_or_predicate, token),
                None,
            )
        )

    @overload
    def remove(self, index: int) -> Self:
        """Remove the token at the given index."""

    @overload
    def remove(self, predicate: Callable[[T], bool]) -> Self:
        """Remove the first token that satisfies the predicate."""

    def remove(self, index_or_predicate: int | Callable[[T], bool]) -> Self:
        def _remove(it: Self, index_or_predicate: int | Callable[[T], bool]):
            removed = False
            for i, t in enumerate(it):
                if removed:
                    yield t
                else:
                    if isinstance(index_or_predicate, int):
                        if i == index_or_predicate:
                            removed = True
                        else:
                            yield t
                    else:
                        if index_or_predicate(t):
                            removed = True
                        else:
                            yield t

        return self._transform(
            Transformation(
                "remove", lambda sequence: _remove(sequence, index_or_predicate), None
            )
        )

    def swap(self, id1, id2) -> Self:
        def _swap(it: Self, id1, id2):
            for i, t in enumerate(it):
                if i == id1:
                    yield it[id2]
                elif i == id2:
                    yield it[id1]
                else:
                    yield t

        return self._transform(
            Transformation("swap", lambda sequence: _swap(sequence, id1, id2), None)
        )
