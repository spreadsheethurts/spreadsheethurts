from typing import Optional
from decimal import Decimal
import sys
from functools import partial, reduce

from ..common.num_alike import (
    Primitive,
    String,
    Composite,
    Placeholder,
    concat_all as concat_all_common,
    concat_sign as concat_sign_common,
    register as register_common,
    NumAlike,
    truncate_to_15_with_zeros,
)


class ExcelNumAlike(NumAlike): ...


TO_NUMBER_HANDER = ExcelNumAlike.HANDLER
register = partial(register_common, handler=TO_NUMBER_HANDER)
concat_all = partial(concat_all_common, handler=TO_NUMBER_HANDER)
concat_sign = partial(concat_sign_common, handler=TO_NUMBER_HANDER)


FLOAT_MIN = sys.float_info.min
FLOAT_MAX = sys.float_info.max


SIGN = Primitive("[+-]").maybe().named("sign")
SPACE = String.space()
ANYSPACE = String.anyspace()
DIGITS = Primitive.digits().named("digits")
INT_DIGITS = Primitive.digits().named("int_digits")

# requires at least a leading digit [1-9], followed by any digits, and groups of at least three digits after each comma.
COMMA_SEPARATED_DIGITS = Primitive(r"(\d*[1-9]\d*)(,\d{3}\d*)+").named(
    "comma_separated_digits"
)
INT_COMMA_SEPARATED_DIGITS = Primitive(r"(\d*[1-9]\d*)(,\d{3}\d*)+").named(
    "int_comma_separated_digits"
)
EXPONENT = Primitive(r"[eE]").named("exponent")
DOT = Primitive.dot().named("dot")
# CURRENCY_SYMBOL = String("¥")  # half-width yen symbol

CURRENCY_SYMBOL = (
    ((String("US").maybe() + String(r"\$")) | String("€") | String("¥"))
    .named("currency_symbol")
    .group()
)
CURRENCY_SYMBOLS_USED_IN_EXAMPLE = ["US$", "$", "€", "¥"]
PERCENT_SYMBOL = String("%")

MAYSIGN_NUMBER_SPACES = (
    (SIGN + Placeholder("num")).join_both_ends(ANYSPACE).named("maysign_number_spaces")
).group()

PARENTHESIS_NUMBER_SPACES = (
    (String(r"\(") + Placeholder("num") + r"\)")
    .join_both_ends(ANYSPACE)
    .named("parenthesis_number_spaces")
).group()

MAY_SIGNED_NUMBER_WITH_SPACES = (
    (MAYSIGN_NUMBER_SPACES | PARENTHESIS_NUMBER_SPACES)
    .named("may_signed_number_with_spaces")
    .group()
)


UNSIGNED_NUMBER_WITH_SPACES = (
    (ANYSPACE + Placeholder("num") + ANYSPACE)
    .named("unsigned_number_with_spaces")
    .group()
)


class IsInteger(ExcelNumAlike):
    INTEGERS = (DIGITS | COMMA_SEPARATED_DIGITS).named("integers").group()
    NUMBER = MAY_SIGNED_NUMBER_WITH_SPACES.format(num=INTEGERS)
    EXAMPLES = ["1", "1,000", "22,333,4445", "-1", "(1,000)", "+22,333,4445"]


def double(coefficient: str, e: str, exponent: str) -> Optional[float]:
    """Convert the coefficient, e, and exponent to a float.

    Positive float strings in the range [2.22507385850721E-308,1e308) are converted to floats,
    while those in [1E-309,2.22507385850721E-308) are converted to 0.0. For values outside these ranges
    (excluding zero), None is returned.
    """

    content = f"{coefficient}{e}{exponent}"
    try:
        decimal = Decimal(content)
    except Exception:
        return None

    if Decimal("2.22507385850721E-308") <= decimal < Decimal("1e308"):
        return float(content)
    elif (
        Decimal("1E-309") <= decimal <= Decimal("2.22507385850721E-308") or decimal == 0
    ):
        return 0.0
    return None


class IsIntegerE(ExcelNumAlike):
    MAY_SIGNED_DIGITS = (SIGN + INT_DIGITS).named("may_signed_digits").group()
    INTEGER_E = (
        (IsInteger.INTEGERS + EXPONENT + MAY_SIGNED_DIGITS).named("integer_e").group()
    )
    NUMBER = MAY_SIGNED_NUMBER_WITH_SPACES.format(num=INTEGER_E)
    EXAMPLES = ["1e1", "1e-1", "1e+1", "11,2233E-11", "(11e1)", "+11e1", "-11e1"]

    @staticmethod
    def may_signed_digits(tree: Composite, groupdict: dict[str, str]) -> Optional[int]:
        return concat_sign(tree, groupdict)

    @staticmethod
    def integer_e(tree: Composite, groupdict: dict[str, str]) -> Optional[float]:
        coe, e, exp = (
            TO_NUMBER_HANDER[pattern.name](pattern, groupdict)
            for pattern in tree.patterns()
        )
        return double(coe, e, exp)


class IsFloat(ExcelNumAlike):
    INTEGERS = (INT_DIGITS | INT_COMMA_SEPARATED_DIGITS).named("integers").group()
    DECIMAL_DIGITS = DIGITS.named("decimal_digits")
    INTEGER_DOT_DIGIT = (INTEGERS + DOT + DECIMAL_DIGITS).named("integer_dot_digit")
    DOT_DIGIT = (DOT + DECIMAL_DIGITS).named("dot_digit")
    INTEGER_DOT = (INTEGERS + DOT).named("integer_dot")

    FLOAT = (INTEGER_DOT_DIGIT | DOT_DIGIT | INTEGER_DOT).named("float").group()

    NUMBER = MAY_SIGNED_NUMBER_WITH_SPACES.format(num=FLOAT)
    EXAMPLES = [
        "22.33",
        "22,333.44",
        "-114.514",
        ".22",
        "22,444.",
        "(22.33)",
        "+22.33",
        "-22.33",
    ]

    @staticmethod
    def decimal_digits(node: Primitive, groupdict: dict[str, str]) -> str:
        return groupdict[node.uid]


class IsFloatE(ExcelNumAlike):
    FLOAT_E = (
        (IsFloat.FLOAT + EXPONENT + IsIntegerE.MAY_SIGNED_DIGITS)
        .named("float_e")
        .group()
    )

    NUMBER = MAY_SIGNED_NUMBER_WITH_SPACES.format(num=FLOAT_E)
    EXAMPLES = [
        "22.33e1",
        "22.33e-1",
        "22.33e+1",
        "22,333.44E-11",
        "(22.33e1)",
        "+22.33e1",
        "-22.33e-1",
    ]

    @staticmethod
    def float_e(tree: Composite, groupdict: dict[str, str]) -> Optional[float]:
        coe, e, exp = (
            TO_NUMBER_HANDER[pattern.name](pattern, groupdict)
            for pattern in tree.patterns()
        )
        return double(coe, e, exp)


class IsFraction(ExcelNumAlike):
    INTEGER_MIXED_FRACTION = (
        (
            IsInteger.INTEGERS
            + SPACE  # exactly one space
            + DIGITS.clone(name="numerator")
            + "/"
            + DIGITS.clone(name="denominator")
        )
        .named("integer_mixed_fraction")
        .group()
    )

    NUMBER = MAY_SIGNED_NUMBER_WITH_SPACES.format(num=INTEGER_MIXED_FRACTION)

    EXAMPLES = [
        "1 1/2",
        "11,514 1/32767",
        "-1 0/32767",
        "(33,333 2223/8899)",
        "-222 333/11",
    ]

    @staticmethod
    def _numerator_denominator_common_check(
        node: Primitive, groupdict: dict[str, str]
    ) -> Optional[int]:
        """The numerator and denominator, once converted to integers, should be less than 32,767.
        Additionally, since int() ignores leading zeros while Excel does not, we need to ensure the numerator’s length is less than 6.
        """
        value = groupdict[node.uid]
        if value.startswith("0"):
            # the length of num should not be greater than 6 (32)
            if len(value) >= 6:
                return None
        elif int(value) > 32767:
            return None
        return int(value)

    @staticmethod
    def numerator(node: Primitive, groupdict: dict[str, str]) -> Optional[int]:
        return IsFraction._numerator_denominator_common_check(node, groupdict)

    @staticmethod
    def denominator(node: Primitive, groupdict: dict[str, str]) -> Optional[int]:
        # Two passes for the denominator, first for is_zero and second for the range.
        if int(groupdict[node.uid]) == 0:
            return None
        return IsFraction._numerator_denominator_common_check(node, groupdict)

    @staticmethod
    def integer_mixed_fraction(tree: Composite, groupdict: dict[str, str]) -> float:
        rets = [
            TO_NUMBER_HANDER[pattern.name](pattern, groupdict)
            for pattern in tree.patterns()
        ]
        if all(ret is not None for ret in rets):
            return rets[0] + rets[1] / rets[2]
        return None


class IsPercent(ExcelNumAlike):
    PERCENT_NUMBER = (
        IsInteger.INTEGERS
        | IsIntegerE.INTEGER_E
        | IsFloat.FLOAT
        | IsFloatE.FLOAT_E
        | IsFraction.INTEGER_MIXED_FRACTION
    ).named("percent_number")

    # 1. 114514%
    NUMBER_WITH_PERCENT = MAY_SIGNED_NUMBER_WITH_SPACES.format(
        num=(PERCENT_NUMBER + ANYSPACE + PERCENT_SYMBOL).named("number_with_percent")
    )

    # 2. %114514
    PERCENT_WITH_NUMBER = MAY_SIGNED_NUMBER_WITH_SPACES.format(
        num=(PERCENT_SYMBOL + ANYSPACE + PERCENT_NUMBER).named("percent_with_number")
    )

    # 3. %-114514 | %(114514)
    PERCENT_WITH_SIGNED_NUMBER = (
        (PERCENT_SYMBOL + SIGN + PERCENT_NUMBER)
        .join_both_ends(ANYSPACE)
        .named("percent_signed_number")
        | (
            ANYSPACE
            + PERCENT_SYMBOL
            + PARENTHESIS_NUMBER_SPACES.format(num=PERCENT_NUMBER)
        ).named("percent_parenthesis_number")
    ).named("percent_with_signed_number")

    # 4. -114514% | (-114514)%
    SIGNED_NUMBER_WITH_PERCENT = (
        (SIGN + PERCENT_NUMBER + PERCENT_SYMBOL)
        .join_both_ends(ANYSPACE)
        .named("signed_number_percent")
        | (
            PARENTHESIS_NUMBER_SPACES.format(num=PERCENT_NUMBER)
            + PERCENT_SYMBOL
            + ANYSPACE
        ).named("parenthesis_number_percent")
    ).named(
        "signed_number_with_percent",
    )

    NUMBER = (
        NUMBER_WITH_PERCENT
        | PERCENT_WITH_NUMBER
        | PERCENT_WITH_SIGNED_NUMBER
        | SIGNED_NUMBER_WITH_PERCENT
    ).named("percent")

    EXAMPLES = [
        "%-114514",
        "-%11,4514",
        "(%55 0/32766)",
        "+%33",
        "%(22,333)",
        "%(1 1/1)",
        "0%",
    ]

    # Check all subpatterns for validity and return the result. Use prefix _ to avoid name conflicts.
    @staticmethod
    def _validate_percent(
        tree: Composite, groupdict: dict[str, str]
    ) -> Optional[int | float]:
        if (ret := concat_all(tree, groupdict)) is not None:
            return ret / 100
        return None

    @staticmethod
    def number_with_percent(
        tree: Composite, groupdict: dict[str, str]
    ) -> Optional[int | float]:
        return IsPercent._validate_percent(tree, groupdict)

    @staticmethod
    def percent_with_number(
        tree: Composite, groupdict: dict[str, str]
    ) -> Optional[int | float]:
        return IsPercent._validate_percent(tree, groupdict)

    @staticmethod
    def percent_signed_number(
        tree: Composite, groupdict: dict[str, str]
    ) -> Optional[int | float]:
        return IsPercent._validate_percent(tree, groupdict)

    @staticmethod
    def percent_parenthesis_number(
        tree: Composite, groupdict: dict[str, str]
    ) -> Optional[int | float]:
        return IsPercent._validate_percent(tree, groupdict)

    @staticmethod
    def signed_number_percent(
        tree: Composite, groupdict: dict[str, str]
    ) -> Optional[int | float]:
        return IsPercent._validate_percent(tree, groupdict)

    @staticmethod
    def parenthesis_number_percent(
        tree: Composite, groupdict: dict[str, str]
    ) -> Optional[int | float]:
        return IsPercent._validate_percent(tree, groupdict)


class IsCurrency(ExcelNumAlike):
    CURRENCY_NUMBER = (
        IsInteger.INTEGERS
        | IsIntegerE.INTEGER_E
        | IsFloat.FLOAT
        | IsFloatE.FLOAT_E
        | IsFraction.INTEGER_MIXED_FRACTION
    ).named("currency_number")

    # 1. $-114514
    CURRENCY_SIGNED_NUMBER = (
        (CURRENCY_SYMBOL + SIGN + CURRENCY_NUMBER)
        .join_both_ends(ANYSPACE)
        .named("currency_signed_number")
    )

    # 2. $(22,333)
    CURRENCY_PARENTHESIS = (
        (CURRENCY_SYMBOL + PARENTHESIS_NUMBER_SPACES.format(num=CURRENCY_NUMBER))
        .join_both_ends(ANYSPACE)
        .named("currency_parenthesis")
    )

    # 3. ($33)
    CURRENCY_WITH_NUMBER = (
        (CURRENCY_SYMBOL + CURRENCY_NUMBER)
        .join_both_ends(ANYSPACE)
        .named("currency_with_number")
    )
    SIGNED_CURRENCY_NUMBER = MAY_SIGNED_NUMBER_WITH_SPACES.format(
        num=CURRENCY_WITH_NUMBER
    )

    NUMBER = (
        CURRENCY_SIGNED_NUMBER | CURRENCY_PARENTHESIS | SIGNED_CURRENCY_NUMBER
    ).named("currency")

    EXAMPLES = list(
        reduce(
            lambda x, y: x + y,
            (
                [
                    rf"{CURRENCY_SYMBOL_USED_IN_EXAMPLE}-114514",
                    rf"-{CURRENCY_SYMBOL_USED_IN_EXAMPLE}11,4514",
                    rf"({CURRENCY_SYMBOL_USED_IN_EXAMPLE}55 0/32766)",
                    rf"+{CURRENCY_SYMBOL_USED_IN_EXAMPLE}33",
                    rf"{CURRENCY_SYMBOL_USED_IN_EXAMPLE}(22,333)",
                    rf"{CURRENCY_SYMBOL_USED_IN_EXAMPLE}(1 1/1)",
                ]
                for CURRENCY_SYMBOL_USED_IN_EXAMPLE in CURRENCY_SYMBOLS_USED_IN_EXAMPLE
            ),
        )
    )

    @staticmethod
    def currency_symbol(_node: Primitive, _groupdict: dict[str, str]) -> str:
        # THIS IS INTENTIONAL
        return ""


@register
def digits(node: Primitive, groupdict: dict[str, str]) -> int | float:
    return truncate_to_15_with_zeros(groupdict[node.uid])


@register
def int_digits(node: Primitive, groupdict: dict[str, str]) -> int:
    if (ret := digits(node, groupdict)) is not None:
        return int(ret)
    return None


@register
def comma_separated_digits(node: Primitive, groupdict: dict[str, str]) -> int | float:
    """Convert the comma separated digits to an integer using the python tokenizer."""
    return truncate_to_15_with_zeros(groupdict[node.uid].replace(",", ""))


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
