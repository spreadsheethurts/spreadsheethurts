from typing import Optional
import math
import sys
from decimal import Decimal
import builtins
from functools import partial

from ...common.num_alike import (
    Primitive,
    String,
    Composite,
    Placeholder,
    register as register_common,
    concat_sign as concat_sign_common,
    concat_all as concat_all_common,
    NumAlike,
    truncate_to_15_with_zeros,
)


class CalcNumAlike(NumAlike): ...


TO_NUMBER_HANDER = CalcNumAlike.HANDLER
register = partial(register_common, handler=TO_NUMBER_HANDER)
concat_all = partial(concat_all_common, handler=TO_NUMBER_HANDER)
concat_sign = partial(concat_sign_common, handler=TO_NUMBER_HANDER)


FLOAT_MIN = sys.float_info.min
FLOAT_MAX = sys.float_info.max


SIGN = Primitive("[+-]").maybe().named("sign")
SPACE = String.space()
ANYSPACE = String.anyspace()
SOMESPACE = String.somespace()
DIGITS = Primitive.digits().named("digits")
INT_DIGITS = Primitive.digits().named("int_digits")

COMMA_SEPARATED_DIGITS = Primitive(r"(\d+)(,\d{3})+").named("comma_separated_digits")
INT_COMMA_SEPARATED_DIGITS = Primitive(r"(\d+)(,\d{3})+").named(
    "int_comma_separated_digits"
)
EXPONENT = Primitive.exponent().named("exponent")
DOT = Primitive.dot().named("dot")
# CURRENCY_SYMBOL = String("￥")  # full-width yen symbol
# CURRENCY_SYMBOL_EXAMPLE = "￥"
CURRENCY_SYMBOL = String(r"\$")
CURRENCY_SYMBOL_EXAMPLE = "$"
PERCENT_SYMBOL = String("%")

MAYSIGN_NUMBER_SPACES = (
    (SIGN + Placeholder("num")).join_both_ends(ANYSPACE).named("maysign_number_spaces")
)

NUMBER_MAYSIGN_SPACES = (
    (Placeholder("num") + SIGN).join_both_ends(ANYSPACE).named("number_maysign_spaces")
)
# String has implemented __add__ but str and Placeholder have not
PARENTHESIS_NUMBER_SPACES = (
    (String(r"\(") + Placeholder("num") + r"\)")
    .join_both_ends(ANYSPACE)
    .named("parenthesis_number_spaces")
)

MAY_SIGNED_NUMBER_WITH_SPACES = (
    MAYSIGN_NUMBER_SPACES | NUMBER_MAYSIGN_SPACES | PARENTHESIS_NUMBER_SPACES
).named("may_signed_number_with_spaces")


UNSIGNED_NUMBER_WITH_SPACES = (ANYSPACE + Placeholder("num") + ANYSPACE).named(
    "unsigned_number_with_spaces"
)


def double(coefficient: str, e: str, exponent: str) -> Optional[float]:
    """Convert the coefficient, e, and exponent to a float.

    Positive float strings greater than FLOAT_MAX are treated as FLOAT_MAX, while those smaller than FLOAT_MIN are treated as 0.0.
    All values within this range are considered valid floats.
    """

    content = f"{coefficient}{e}{exponent}"
    try:
        decimal = Decimal(content)
    except Exception:
        return None

    if decimal > FLOAT_MAX:
        return FLOAT_MAX

    elif decimal <= FLOAT_MIN:
        return 0.0

    return builtins.float(decimal)


class IsInteger(CalcNumAlike):
    INTEGERS = (DIGITS | COMMA_SEPARATED_DIGITS).named("integers").group()
    NUMBER = MAY_SIGNED_NUMBER_WITH_SPACES.format(num=INTEGERS)
    EXAMPLES = [
        "0,333,444",
        "000222,333,333",
        "+0003333",
        "-1000",
        "(1,000)",
        "90071992547409921111111111111111111111",
        "9,007,199,254,740,992",
    ]


class IsIntegerE(CalcNumAlike):
    MAY_SIGNED_DIGITS = (SIGN + INT_DIGITS).named("may_signed_digits").group()
    # Note: exponent can be followed by a optional dot
    INTEGER_E = (
        (
            IsInteger.INTEGERS
            + ANYSPACE
            + EXPONENT
            + ANYSPACE
            + MAY_SIGNED_DIGITS
            + String.dot().maybe()
        )
        .named("integer_e")
        .group()
    )
    NUMBER = MAY_SIGNED_NUMBER_WITH_SPACES.format(num=INTEGER_E)
    EXAMPLES = ["1e1", "1e-1", "1e+1", "11,223E-11", "(11e1)", "+11e1", "-11e1", "2e 1"]

    @staticmethod
    def may_signed_digits(tree: Composite, groupdict: dict[str, str]) -> Optional[int]:
        return concat_sign(tree, groupdict)

    @staticmethod
    def integer_e(tree: Composite, groupdict: dict[str, str]) -> float:
        coe, e, exp = (
            TO_NUMBER_HANDER[pattern.name](pattern, groupdict)
            for pattern in tree.patterns()
        )
        return double(coe, e, exp)


class IsFloat(CalcNumAlike):
    INTEGERS = (INT_DIGITS | INT_COMMA_SEPARATED_DIGITS).named("integers").group()
    DECIMAL_DIGITS = DIGITS.named("decimal_digits")
    INTEGER_DOT_DIGIT = (
        (INTEGERS + DOT + DECIMAL_DIGITS).named("integer_dot_digit").group()
    )
    DOT_DIGIT = (DOT + DECIMAL_DIGITS).named("dot_digit").group()
    INTEGER_DOT = (INTEGERS + DOT).named("integer_dot").group()

    FLOAT = (INTEGER_DOT_DIGIT | DOT_DIGIT | INTEGER_DOT).named("float").group()
    NUMBER = MAY_SIGNED_NUMBER_WITH_SPACES.format(num=FLOAT)
    EXAMPLES = [
        "22.33",
        "22,333.44",
        "-114.514",
        ".22",
        "22,444.",
        "(22.33)",
        "+22,333.33",
        "-22.33",
        "22.33-",
        "22.33+",
    ]

    @staticmethod
    def decimal_digits(node: Primitive, groupdict: dict[str, str]) -> str:
        return groupdict[node.uid]


class IsFloatE(CalcNumAlike):
    FLOAT_E = (
        (IsFloat.FLOAT + ANYSPACE + EXPONENT + ANYSPACE + IsIntegerE.MAY_SIGNED_DIGITS)
        .named("float_e")
        .group()
    )
    NUMBER = MAY_SIGNED_NUMBER_WITH_SPACES.format(num=FLOAT_E)
    EXAMPLES = [
        "22,333.33e1",
        ".33e-1",
        "22.e+1",
        "22,333.44E-11",
        "(22.33e1)",
        "+.33e1",
        "-22.e-1",
        "22.e-1-",
        "22.e-1+",
    ]

    @staticmethod
    def float_e(tree: Composite, groupdict: dict[str, str]) -> float:
        coe, e, exp = (
            TO_NUMBER_HANDER[pattern.name](pattern, groupdict)
            for pattern in tree.patterns()
        )
        return double(coe, e, exp)


class IsFraction(CalcNumAlike):
    INTEGER_MIXED_FRACTION = (
        (
            DIGITS
            + SOMESPACE
            + DIGITS
            + ANYSPACE
            + "/"
            + ANYSPACE
            + DIGITS.clone("denominator")
        )
        .named("integer_mixed_fraction")
        .group()
    )

    NUMBER = MAY_SIGNED_NUMBER_WITH_SPACES.format(num=INTEGER_MIXED_FRACTION)

    EXAMPLES = [
        "1 1/2",
        "11 1/99999",
        "-1 0/111",
        "(333 2223/8899)",
        "+222 333/11",
    ]

    @staticmethod
    def denominator(node: Primitive, groupdict: dict[str, str]) -> Optional[int]:
        # The denominator should not be zero.
        if (value := int(groupdict[node.uid])) == 0:
            return None

        return value

    @staticmethod
    def integer_mixed_fraction(tree: Composite, groupdict: dict[str, str]) -> float:
        rets = [
            TO_NUMBER_HANDER[pattern.name](pattern, groupdict)
            for pattern in tree.patterns()
        ]
        if all(ret is not None for ret in rets):
            return rets[0] + rets[1] / rets[2]
        return None


class IsPercent(CalcNumAlike):
    PERCENT_NUMBER = (
        (IsInteger.INTEGERS | IsFloat.FLOAT).named("percent_number").group()
    )

    SIGNED_NUMBER_WITH_PERCENT = (
        (MAY_SIGNED_NUMBER_WITH_SPACES.format(num=PERCENT_NUMBER) + PERCENT_SYMBOL)
        .named("signed_number_with_percent")
        .group()
    )

    NUMBER = UNSIGNED_NUMBER_WITH_SPACES.format(num=SIGNED_NUMBER_WITH_PERCENT)

    EXAMPLES = [
        "-114514%",
        "-11,451%",
        "(55.)%",
        "2.33-%",
        "-33%",
        "+11.22%",
    ]

    @staticmethod
    def signed_number_with_percent(
        tree: Composite, groupdict: dict[str, str]
    ) -> Optional[float | int]:
        if (num := concat_all(tree, groupdict)) is not None:
            return num / 100
        return None


class IsCurrency(CalcNumAlike):
    CURRENCY_NUMBER = (IsInteger.INTEGERS | IsFloat.FLOAT).named("currency_number")

    # 1. currency prefix with signed number: $-1, $1-, $+1, $(1)
    CURRENCY_PREFIX_SIGNED_NUMBER = (
        (
            CURRENCY_SYMBOL
            + ANYSPACE
            + MAY_SIGNED_NUMBER_WITH_SPACES.format(num=CURRENCY_NUMBER)
        )
        .named("currency_prefix_signed_number")
        .group()
    )

    # 2. currency prefix with unsigned number: $1
    CURRENCY_PREFIX_UNSIGNED_NUMBER = (
        (CURRENCY_SYMBOL + ANYSPACE + CURRENCY_NUMBER)
        .named("currency_prefix_unsigned_number")
        .group()
    )

    # 3. currency suffix with signed number: -1$, (1)$, +1$, 1-$
    CURRENCY_SUFFIX_SIGNED_NUMBER = (
        (
            MAY_SIGNED_NUMBER_WITH_SPACES.format(num=CURRENCY_NUMBER)
            + CURRENCY_SYMBOL
            + ANYSPACE
        )
        .named("currency_suffix_signed_number")
        .group()
    )

    # 4. currency suffix with unsigned number in parentheses: (1$)
    NUMBER_WITH_CURRENCY_IN_PARENTHESIS = PARENTHESIS_NUMBER_SPACES.format(
        num=(CURRENCY_NUMBER + ANYSPACE + CURRENCY_SYMBOL + ANYSPACE).named(
            "number_with_currency_in_parentheses"
        )
    ).group()

    NUMBER = (
        MAY_SIGNED_NUMBER_WITH_SPACES.format(num=CURRENCY_PREFIX_UNSIGNED_NUMBER)
        | UNSIGNED_NUMBER_WITH_SPACES.format(num=CURRENCY_PREFIX_SIGNED_NUMBER)
        | CURRENCY_SUFFIX_SIGNED_NUMBER
        | NUMBER_WITH_CURRENCY_IN_PARENTHESIS
    ).named("currency")

    EXAMPLES = [
        rf"{CURRENCY_SYMBOL_EXAMPLE}-114514",
        rf"{CURRENCY_SYMBOL_EXAMPLE}(11,451.22)",
        rf"{CURRENCY_SYMBOL_EXAMPLE}.22-",
        rf"-{CURRENCY_SYMBOL_EXAMPLE}11,451",
        rf"({CURRENCY_SYMBOL_EXAMPLE}55.223)",
        rf"+{CURRENCY_SYMBOL_EXAMPLE}333",
        rf"12.34 {CURRENCY_SYMBOL_EXAMPLE} ",
    ]


@register
def digits(node: Primitive, groupdict: dict[str, str]) -> int:
    digits = groupdict[node.uid]
    if int(digits) <= 2**53 - 1:
        return int(digits)

    return truncate_to_15_with_zeros(digits)


@register
def int_digits(node: Primitive, groupdict: dict[str, str]) -> int:
    if (ret := digits(node, groupdict)) is not None:
        return int(ret)
    return None


@register
def comma_separated_digits(node: Primitive, groupdict: dict[str, str]) -> int:
    """Convert the thousands digits to an integer using the python tokenizer."""
    digits = groupdict[node.uid].replace(",", "")
    if int(digits) <= 2**53 - 1:
        return int(digits)

    return truncate_to_15_with_zeros(digits)


@register
def int_comma_separated_digits(node: Primitive, groupdict: dict[str, str]) -> int:
    if (ret := comma_separated_digits(node, groupdict)) is not None:
        return int(ret)
    return None


@register("sign", "exponent", "dot")
def primitive(node: Primitive, groupdict: dict[str, str]) -> str:
    return groupdict[node.uid]


@register
def maysign_number_spaces(
    tree: Composite, groupdict: dict[str, str]
) -> Optional[float | int]:
    return concat_sign(tree, groupdict)


@register
def number_maysign_spaces(
    tree: Composite, groupdict: dict[str, str]
) -> Optional[float | int]:
    # Since Python’s tokenizer doesn’t recognize text like 1- as the number -1, we handle this case manually.
    num, sign = (
        TO_NUMBER_HANDER[pattern.name](pattern, groupdict)
        for pattern in tree.patterns()
    )
    if math.fabs(num) == sys.float_info.max:
        return sys.float_info.max
    if num:
        match sign:
            case "+":
                return num
            case "-":
                return -num
            # If the sign is not specified, it is positive.
            case None:
                return num
    return None


@register
def parenthesis_number_spaces(
    tree: Composite, groupdict: dict[str, str]
) -> Optional[float | int]:
    if (ret := concat_all(tree, groupdict)) is not None:
        return -ret
    return None


@register
def unsigned_number_with_spaces(
    tree: Composite, groupdict: dict[str, str]
) -> Optional[float | int]:
    return concat_all(tree, groupdict)
