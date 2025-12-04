def group(*choices) -> str:
    return "(" + "|".join(choices) + ")"


def any(*choices) -> str:
    return group(*choices) + "*"


def some(*choices) -> str:
    return group(*choices) + "+"


def maybe(*choices) -> str:
    return group(*choices) + "?"


def named(regex: str, name: str) -> str:
    return f"(?P<{name}>{regex})"


def join_with_suffix(*choices, suffix: str = "") -> str:
    return suffix.join(choices) + suffix


def join_with_prefix_suffix(*choices, sep: str = "") -> str:
    return sep + sep.join(choices) + sep


def backreference(name: str) -> str:
    return f"(?P={name})"
