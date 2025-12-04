from typing import Optional, Callable, TypeAlias
import re
from functools import partial

from wizard.feature import Feature
from ..pattern import Pattern, Composite
from wizard.typ import Int, Float, to_number

PUNCTUATION: TypeAlias = str
NUMBER_TYPE: TypeAlias = Int | Float
LEXICON: TypeAlias = PUNCTUATION | NUMBER_TYPE
HANDLER_TYPE: TypeAlias = Callable[[Pattern, dict], Optional[LEXICON]]

TO_NUMBER_HANDER: dict[str, HANDLER_TYPE] = {}


def register(*args, handler: dict[str, HANDLER_TYPE]) -> HANDLER_TYPE:
    """Specifies the names under which to register the function in the handlers. If no names are provided, the function’s original name is used.

    The function acts as both a validator and a to_number handler: if it returns None, validation has failed;
    otherwise, it returns the corresponding numerical value. The function can return a string, integer, or float.
    If it returns a string, either the top-level Python tokenizer or other handlers will combine the string
    with other numerical values to form a single number.
    """
    # decorator called without parentheses
    if len(args) == 1 and callable(args[0]):
        func = args[0]
        handler[func.__name__] = func
        return func

    # decorator called with specific names
    def do_register(func) -> HANDLER_TYPE:
        for name in args:
            handler[name] = func
        return func

    return do_register


def group(
    node: Composite, groupdict: dict[str, str], handler: dict[str, HANDLER_TYPE]
) -> Optional[int | float]:
    """Locate the actual composite pattern and extract its numerical value."""
    actual_node = node.patterns()[0]
    return handler[actual_node.name](actual_node, groupdict)


def branch(
    node: Composite, groupdict: dict[str, str], handler: dict[str, HANDLER_TYPE]
) -> Optional[int | float]:
    """Locate the single branch and extract its numerical value."""
    for branch in node.patterns():
        if branch.uid in groupdict and groupdict[branch.uid] is not None:
            return handler[branch.name](branch, groupdict)
    return None


def concat_all(
    tree: Composite, groupdict: dict[str, str], handler: dict[str, HANDLER_TYPE]
) -> Optional[int | float]:
    """Concatenates all non-None values from a sequence of patterns into a single numerical value using Python's float tokenizer.

    Returns None if any pattern yields None, otherwise returns an integer or float based on the concatenated result.
    """
    rets = [handler[pattern.name](pattern, groupdict) for pattern in tree.patterns()]
    # 0 will be treated as False by all()
    if all(ret is not None for ret in rets):
        num = eval("".join(map(str, rets)))
        if isinstance(num, (int, float)):
            return num
        raise ValueError(f"Invalid number: {num}")
    else:
        return None


def concat_sign(
    tree: Composite, groupdict: dict[str, str], handler: dict[str, HANDLER_TYPE]
) -> Optional[float | int]:
    """Concatenates values from a sequence of patterns into a single numerical value, allowing sign patterns to be None.

    Only patterns named 'sign', 'minus', or 'plus' are allowed to be None or empty strings. All other patterns must have
    valid values. The concatenated string is evaluated using Python's eval() to produce the final numerical result.
    """
    rets = []
    for pattern in tree.patterns():
        num = handler[pattern.name](pattern, groupdict)
        if (
            # sign can be empty string
            num is None
            or num == ""
            and pattern.name
            not in [
                "sign",
                "minus",
                "plus",
            ]
        ):
            return None
        rets.append(num)
    num = eval("".join(map(str, rets)))
    if isinstance(num, (int, float)):
        return num
    raise ValueError(f"Invalid number: {num}")


def concat_any(
    tree: Composite, groupdict: dict[str, str], handler: dict[str, HANDLER_TYPE]
) -> Optional[int | float]:
    """Concatenates non-None values from a sequence of patterns into a single numerical value using Python's float tokenizer.

    Returns None if no pattern yields a valid value; otherwise, returns an integer or float based on the concatenated result.
    Useful for cases where a specific pattern is optional (e.g., ‘?’ qualifier in regex).
    """
    rets = list(
        filter(
            lambda x: x is not None,
            [handler[pattern.name](pattern, groupdict) for pattern in tree.patterns()],
        )
    )
    if rets:
        num = eval("".join(map(str, rets)))
        if isinstance(num, (int, float)):
            return num
        raise ValueError(f"Invalid number: {num}")
    else:
        return None


def register_subclass(subclass: type, handler: dict[str, HANDLER_TYPE]):
    """Registers all class variables of type Composite and their child patterns with default handlers and static methods as custom handlers.

    This function iterates over the class's variables and methods, collecting all instances of Composite and any static methods.
    For each Composite instance found:
    - The top-level Composite and all its nested child patterns are registered with default handlers
    - The handler type is determined by whether the pattern is a branch, group, or sequence pattern

    Static methods have higher priority than class variable handlers, which serve as default handlers.
    """

    trees: list[Composite] = []
    staticmethods = []
    for name, value in subclass.__dict__.items():
        if name.startswith("__"):
            continue

        if not callable(value) and isinstance(value, Composite):
            trees.append(value)
        elif isinstance(value, staticmethod):
            staticmethods.append(value)

    for method in staticmethods:
        register(method, handler=handler)

    for tree in trees:

        def register_tree(t: Composite):
            if not t.name and t.is_group:
                t.name = "group"

            if t.name and t.name not in handler:
                if t.is_group:
                    handler[t.name] = partial(group, handler=handler)
                elif t.is_branch:
                    handler[t.name] = partial(branch, handler=handler)
                else:
                    handler[t.name] = partial(concat_all, handler=handler)

            # Recursively register handlers for subtrees
            for pattern in t.patterns():
                if isinstance(pattern, Composite):
                    register_tree(pattern)

        register_tree(tree)


def truncate_to_15_with_zeros(digits: str) -> int | float:
    if int(digits) == 0:
        return 0

    digits = digits.lstrip("0")
    if len(digits) <= 15:
        return int(digits)
    return float(digits[:15] + "0" * (len(digits) - 15))


class NumAlike(Feature):
    """A feature class for recognizing numerical strings.

    All class variables of type Composite will be automatically registered with to_number_handler.
    If a Composite represents a multi-branch pattern, it will be registered as a branch handler;
    otherwise, it will be registered as a concat_all handler.
    For cases where users wish to register a custom handler, the NumAlike class will automatically detect
    all static methods in the subclass and register them using the function name as the key.
    (Static methods take priority over class variable handlers, as class variable handlers are default handlers.)
    In other cases, users can manually register a handler by applying the register decorator.
    """

    TYPE = "Number"
    NUMBER: Optional[Composite] = None
    PATTERN: re.Pattern = None

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        parent = cls.__bases__[0]
        # whose parent is NumAlike
        if parent == NumAlike:
            cls.HANDLER: dict[str, HANDLER_TYPE] = {}
        # whose grandparent is NumAlike
        else:
            register_subclass(cls, parent.HANDLER)

    @classmethod
    def is_num_valid(cls, num: str) -> Optional[NUMBER_TYPE]:
        if groupdict := cls.fullmatch(num):
            # Filter out None values from groupdict
            groupdict = {k: v for k, v in groupdict.items() if v is not None}
            if (val := cls.HANDLER[cls.NUMBER.name](cls.NUMBER, groupdict)) is not None:
                return to_number(val)
        return None

    @classmethod
    def fullmatch(cls, content: str) -> Optional[dict[str, str]]:
        if cls.PATTERN is None:
            cls.NUMBER = cls.NUMBER.clone()
            cls.PATTERN = cls.NUMBER.compile()

        if match := cls.PATTERN.fullmatch(content):
            return match.groupdict()

        return None

    @classmethod
    def evaluate(cls, content: str) -> bool:
        return cls.is_num_valid(content) is not None

    @classmethod
    def to_cell_number(cls, content: str) -> Optional[NUMBER_TYPE]:
        return cls.is_num_valid(content)

    @classmethod
    def to_scalar_number(cls, content: str) -> Optional[NUMBER_TYPE]:
        return cls.is_num_valid(content)
