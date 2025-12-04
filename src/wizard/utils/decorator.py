import asyncio
import os
import sys
import time
from functools import wraps
from typing import Callable, Type, TypeVar, ParamSpec, Protocol, Any

import rich


class Cell(Protocol):
    content: Any


def ensure_str_cast(func: Callable[[Type, Cell], bool]) -> Callable[[Type, Cell], bool]:
    """Verifies that the content of a cell can be converted to a string without containing newlines."""

    @wraps(func)
    def inner(cls, cell: Cell):
        try:
            content = str(cell.content)
        except TypeError:
            return False
        # check if the content contains newline characters
        if "\n" in content:
            return False

        return func(cls, cell)

    return inner


P = ParamSpec("P")
R = TypeVar("R")


def timeit(func: Callable[P, R]) -> Callable[P, R]:
    """Decorator that times the execution of a function."""

    @wraps(func)
    def inner(*args: P.args, **kwargs: P.kwargs) -> R:

        start = time.time()
        result = func(*args, **kwargs)
        rich.print(f"{func.__qualname__} took {time.time() - start: .4f} seconds")
        return result

    @wraps(func)
    async def inner_async(*args: P.args, **kwargs: P.kwargs) -> R:

        start = time.time()
        result = await func(*args, **kwargs)
        rich.print(f"{func.__qualname__} took {time.time() - start: .4f} seconds")
        return result

    if asyncio.iscoroutinefunction(func):
        return inner_async
    else:
        return inner


def suppress_output(func: Callable) -> Callable:
    """Decorator that suppresses the output of a function."""

    @wraps(func)
    def inner(*args, **kwargs):
        with open(os.devnull, "w") as f:
            sys.stdout = f
            sys.stderr = f
            result = func(*args, **kwargs)
            sys.stdout = sys.__stdout__
            sys.stdout = sys.__stderr__
        return result

    return inner
