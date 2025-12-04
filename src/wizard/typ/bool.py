from .number import Int


class Bool(Int):
    def __new__(cls, value):
        b = 1 if value else 0
        return super().__new__(cls, b)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({bool(self)})"

    def to_number(self) -> Int:
        return Int(self)
