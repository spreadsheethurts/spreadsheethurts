import string
import random
from typing import Self, Generator

from wizard.token.base import Token


def relu(x: int | float) -> int:
    return int(max(0, x))


class Digit(Token):
    """Represents an integer."""

    SCOPE = list(string.digits)

    def __init__(self, digits: str):
        assert digits.isdigit(), f"Invalid digits: {digits}"
        super().__init__(digits)
        self.number = int(digits)

    def isdigit(self) -> bool:
        return True

    def transform(self) -> Generator[Self, None, None]:
        yield from self.leading_zeros()

        for i in range(-random.randint(1, 200), random.randint(1, 200)):
            yield self + i
            yield self * i
            if i != 0:
                yield self / i
                yield self // i
                yield self % i

    def leading_zeros(self) -> Generator[Self, None, None]:
        """Yield digits with leading zeros."""
        for num in range(1, 10):
            yield Digit("0" * num + self.value)

    def lop(self, op: str, rhs: Self | int | float):
        """Apply left operand operation."""

        assert isinstance(
            rhs, int | float | Digit
        ), f"Cannot apply '{op}' between {self.__class__.__name__} and {rhs.__class__.__name__} "
        opd = rhs if isinstance(rhs, int | float) else rhs.number
        return Digit(str(relu(eval(f"{self.number} {op} {opd}"))))

    def rop(self, op: str, lhs: Self | int | float):
        """Apply right operand operation."""

        assert isinstance(
            lhs, int | float | Digit
        ), f"Cannot apply '{op}' between {lhs.__class__.__name__} and {self.__class__.__name__} "
        opd = lhs if isinstance(lhs, int | float) else lhs.number
        return Digit(str(relu(eval(f"{opd} {op} {self.number}"))))

    def __add__(self, other: Self | int | float) -> Self:
        return self.lop("+", other)

    def __radd__(self, other: Self | int | float) -> Self:
        return self.rop("+", other)

    def __mul__(self, other: Self | int | float) -> Self:
        return self.lop("*", other)

    def __rmul__(self, other: Self | int | float) -> Self:
        return self.rop("*", other)

    def __sub__(self, other: Self | int | float) -> Self:
        return self.lop("-", other)

    def __rsub__(self, other: Self | int | float) -> Self:
        return self.rop("-", other)

    def __floordiv__(self, other: Self | int | float) -> Self:
        return self.lop("//", other)

    def __rfloordiv__(self, other: Self | int | float) -> Self:
        return self.rop("//", other)

    def __truediv__(self, other: Self | int | float) -> Self:
        return self.lop("/", other)

    def __rtruediv__(self, other: Self | int | float) -> Self:
        return self.rop("/", other)

    def __mod__(self, other: Self | int | float) -> Self:
        return self.lop("%", other)

    def __rmod__(self, other: Self | int | float) -> Self:
        return self.rop("%", other)
