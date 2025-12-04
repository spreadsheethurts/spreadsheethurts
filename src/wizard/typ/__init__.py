from .text import Text
from .number import Int, Float, to_number
from .bool import Bool
from .datetime import *


class UniversalEqual:
    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        return True

    def __repr__(self):
        return f"{self.__class__.__name__}({repr(self.value)})"

    def __str__(self):
        return str(self.value)


class Discard(UniversalEqual): ...


class Weird(UniversalEqual): ...
