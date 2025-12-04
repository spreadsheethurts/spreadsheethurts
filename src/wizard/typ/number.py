from math import isclose


def _create_wrapped_method(original_method):
    """Factory to create a method that wraps results in the class type."""

    def wrapped_method(self, other):
        result = original_method(self, other)
        return NotImplemented if result is NotImplemented else self.__class__(result)

    return wrapped_method


class ArithmeticWrapMeta(type):
    """Metaclass to wrap arithmetic methods to return the class type."""

    def __new__(cls, name, bases, dct):
        # fmt: off
        OPERATORS = {
            # forward
            '__add__', '__sub__', '__mul__', '__truediv__', '__floordiv__',
            '__mod__', '__pow__', '__lshift__', '__rshift__', '__and__',
            '__xor__', '__or__',
            # reverse
            '__radd__', '__rsub__', '__rmul__', '__rtruediv__', '__rfloordiv__',
            '__rmod__', '__rpow__', '__rlshift__', '__rrshift__', '__rand__',
            '__rxor__', '__ror__',
            # in-place
            '__iadd__', '__isub__', '__imul__', '__itruediv__', '__ifloordiv__',
            '__imod__', '__ipow__', '__ilshift__', '__irshift__', '__iand__',
            '__ixor__', '__ior__',
        }
        # fmt: on

        parent_type = None
        for base in bases:
            if base in (type, float):
                parent_type = base
                break

        if parent_type is None:
            return super().__new__(cls, name, bases, dct)

        for method_name in OPERATORS:
            # skip if method is already defined
            if method_name not in dct:
                try:
                    original_method = getattr(parent_type, method_name)
                except AttributeError:
                    continue
                dct[method_name] = _create_wrapped_method(original_method)

        return super().__new__(cls, name, bases, dct)


class Int(int, metaclass=ArithmeticWrapMeta):
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.real})"

    def __str__(self) -> str:
        return f"{self.real}"


class Float(float, metaclass=ArithmeticWrapMeta):
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.real})"

    def __str__(self) -> str:
        return f"{self.real}"

    def __eq__(self, other) -> bool:
        if isinstance(other, (float, int)):
            return isclose(self, other)
        return NotImplemented

    def __ne__(self, other) -> bool:
        equal = self.__eq__(other)
        if equal is NotImplemented:
            return NotImplemented
        return not equal


def to_number(value: int | float) -> Int | Float:
    return Int(value) if isinstance(value, int) else Float(value)
