from typing import Optional
from decimal import Decimal
import sys
import builtins
from functools import partial

from wizard.feature import WeirdFeature
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


class GsheetNumAlike(NumAlike): ...


TO_NUMBER_HANDER = GsheetNumAlike.HANDLER
register = partial(register_common, handler=TO_NUMBER_HANDER)
concat_all = partial(concat_all_common, handler=TO_NUMBER_HANDER)
concat_sign = partial(concat_sign_common, handler=TO_NUMBER_HANDER)


FLOAT_MIN = sys.float_info.min
FLOAT_MAX = sys.float_info.max

SIGN_MAYBE = Primitive("[+-]").maybe().named("sign")
SPACE = String.space()
ANYSPACE = String.anyspace()
SOMESPACE = String.somespace()
PLUS = Primitive.plus().named("plus")
PLUS_MAYBE = Primitive.plus().maybe().named("plus")
MINUS_MAYBE = Primitive.minus().maybe().named("minus")
DIGITS = Primitive.digits().named("digits")
INT_DIGITS = Primitive(r"\d+").named("int_digits")
# Matches an optional leading group of digits, followed by one or more comma-separated groups of **at least three digits**.
THOUSANDS_DIGITS = Primitive(r"(\d*)(,\d{3}\d*)+", name="thousands_digits")
INT_THOUSANDS_DIGITS = Primitive(r"(\d*)(,\d{3}\d*)+", name="int_thousands_digits")
EXPONENT = Primitive.exponent().named("exponent")
DOT = Primitive.dot().named("dot")
CURRENCY_SYMBOL = (String.dollar() | String("€")).named("currency_symbol").group()
CURRENCY_SYMBOL_EXAMPLE = "$"
PERCENT_SYMBOL = String("%")


PARENTHESIS_NUMBER = (
    (String(r"\(") + Placeholder("num") + String(r"\)"))
    .named("parenthesis_number")
    .group()
)

PARENTHESIS_NUMBER_SPACES = (
    (String(r"\(") + Placeholder("num") + String(r"\)"))
    .join_both_ends(ANYSPACE)
    .named("parenthesis_number_spaces")
).group()

MAY_MINUS_NUMBER_SPACES = (
    (MINUS_MAYBE + Placeholder("num"))
    .join_both_ends(ANYSPACE)
    .named("may_minus_number_spaces")
)

MAY_SIGNED_NUMBER = (
    (SIGN_MAYBE + Placeholder("num")).named("may_signed_number_") | PARENTHESIS_NUMBER
).named("may_signed_number")

MAY_SIGNED_NUMBER_WITH_SPACES = (
    (
        (SIGN_MAYBE + Placeholder("num"))
        .join_both_ends(ANYSPACE)
        .named("may_sign_number_spaces")
    )
    | PARENTHESIS_NUMBER_SPACES
).named("may_signed_number_with_spaces")

MAY_SIGNED_NUMBER_WITH_CONDITIONAL_SPACING = (
    (SPACE + PLUS + Placeholder("num")).join(ANYSPACE).named("plus_number_spaces")
    | MAY_MINUS_NUMBER_SPACES
    | PARENTHESIS_NUMBER_SPACES
).named("may_signed_number_with_conditional_spacing")

UNSIGNED_NUMBER_WITH_SPACES = (ANYSPACE + Placeholder("num") + ANYSPACE).named(
    "unsigned_number_with_spaces"
)


class IsInteger(GsheetNumAlike):
    NUMBER = (
        MAY_SIGNED_NUMBER_WITH_CONDITIONAL_SPACING.format(num=THOUSANDS_DIGITS)
        | MAY_SIGNED_NUMBER_WITH_SPACES.format(num=DIGITS)
    ).named("integer")
    EXAMPLES = [
        ",000",
        "-22,333,4445",
        "-1",
        "(1,000)",
        " +22,333,4445",
        "123456789012345",
        "00123456789012345000",
    ]
    COUNTER_EXAMPLES = ["9007199254740991"]


def double(coefficient: float, e: str, exponent: int) -> Optional[float]:
    """Convert the coefficient, e, and exponent to a float.

    Positive float strings greater than 1.79769313486232e308 are considered invalid in Google Sheets,
    while values smaller than 2.22507385850721e-308 are treated as 0.0. All other values within this
    range are valid floats.
    """
    content = f"{coefficient}{e}{exponent}"
    try:
        decimal = Decimal(content)
    except Exception:
        return None

    if decimal >= Decimal("1.79769313486232e308"):
        return None

    elif decimal < Decimal("2.22507385850721E-308"):
        return 0.0

    return builtins.float(decimal)


class IsIntegerE(GsheetNumAlike):
    MAY_SIGNED_DIGITS = (SIGN_MAYBE + INT_DIGITS).named("may_signed_digits")
    DIGITS_E = (DIGITS + EXPONENT + MAY_SIGNED_DIGITS).named("digits_e").group()
    THOUSANDS_DIGITS_E = (
        (THOUSANDS_DIGITS + EXPONENT + MAY_SIGNED_DIGITS)
        .named("thousands_digits_e")
        .group()
    )

    NUMBER = (
        MAY_SIGNED_NUMBER_WITH_SPACES.format(num=DIGITS_E)
        | MAY_SIGNED_NUMBER_WITH_CONDITIONAL_SPACING.format(num=THOUSANDS_DIGITS_E)
    ).named("integer_e")
    EXAMPLES = ["1e1", ",000e-1", "11,2233E-11", "(11e1)", "+11e1", "-11e1"]

    @staticmethod
    def may_signed_digits(tree: Composite, groupdict: dict[str, str]) -> Optional[int]:
        return concat_sign(tree, groupdict)

    @staticmethod
    def digits_e(tree: Composite, groupdict: dict[str, str]) -> Optional[float]:
        coe, e, exp = (
            TO_NUMBER_HANDER[pattern.name](pattern, groupdict)
            for pattern in tree.patterns()
        )
        return double(coe, e, exp)

    @staticmethod
    def thousands_digits_e(
        tree: Composite, groupdict: dict[str, str]
    ) -> Optional[float]:
        coe, e, exp = (
            TO_NUMBER_HANDER[pattern.name](pattern, groupdict)
            for pattern in tree.patterns()
        )
        return double(coe, e, exp)


class IsFloat(GsheetNumAlike):
    DECIMAL_DIGITS = INT_DIGITS.named("decimal_digits")
    DIGITS_DOT = (INT_DIGITS + DOT).named("digits_dot")
    DOT_DIGITS = (DOT + DECIMAL_DIGITS).named("dot_digits").group()
    DIGITS_DOT_DIGITS = (INT_DIGITS + DOT + DECIMAL_DIGITS).named("digits_dot_digits")

    THOUSANDS_DIGITS_DOT = (INT_THOUSANDS_DIGITS + DOT).named("thousands_digits_dot")
    THOUSANDS_DIGITS_DOT_DIGITS = (INT_THOUSANDS_DIGITS + DOT + DECIMAL_DIGITS).named(
        "thousands_digits_dot_digits"
    )

    DIGITS_FLOAT = (
        (DIGITS_DOT | DIGITS_DOT_DIGITS | DOT_DIGITS).named("digits_float").group()
    )
    THOUSANDS_DIGITS_FLOAT = (
        (THOUSANDS_DIGITS_DOT | THOUSANDS_DIGITS_DOT_DIGITS)
        .named("thousands_digits_float")
        .group()
    )

    NUMBER = (
        MAY_SIGNED_NUMBER_WITH_SPACES.format(num=DIGITS_FLOAT)
        | MAY_SIGNED_NUMBER_WITH_CONDITIONAL_SPACING.format(num=THOUSANDS_DIGITS_FLOAT)
    ).named("float")

    EXAMPLES = [
        "22.33",
        "22,333.44",
        "-114.514",
        ".22",
        " +22,444.",
        "-22,444.",
        "(22.33)",
    ]

    @staticmethod
    def decimal_digits(node: Primitive, groupdict: dict[str, str]) -> Optional[float]:
        return groupdict[node.uid]


class IsFloatE(GsheetNumAlike):
    DIGITS_FLOAT_E = (
        (IsFloat.DIGITS_FLOAT + EXPONENT + IsIntegerE.MAY_SIGNED_DIGITS)
        .named("digits_float_e")
        .group()
    )
    THOUSANDS_DIGITS_FLOAT_E = (
        (IsFloat.THOUSANDS_DIGITS_FLOAT + EXPONENT + IsIntegerE.MAY_SIGNED_DIGITS)
        .named("thousands_digits_float_e")
        .group()
    )

    NUMBER = (
        MAY_SIGNED_NUMBER_WITH_SPACES.format(num=DIGITS_FLOAT_E)
        | MAY_SIGNED_NUMBER_WITH_CONDITIONAL_SPACING.format(
            num=THOUSANDS_DIGITS_FLOAT_E
        )
    ).named("float_e")

    EXAMPLES = [
        "22.33e1",
        "22.e-1",
        ".33e+1",
        " +22,333.44E-11",
        "(22,333.e+1)",
        "+22.33e1",
        "-22.33e-1",
    ]

    @staticmethod
    def digits_float_e(tree: Composite, groupdict: dict[str, str]) -> Optional[float]:
        coe, e, exp = (
            TO_NUMBER_HANDER[pattern.name](pattern, groupdict)
            for pattern in tree.patterns()
        )
        return double(coe, e, exp)

    @staticmethod
    def thousands_digits_float_e(
        tree: Composite, groupdict: dict[str, str]
    ) -> Optional[float]:
        coe, e, exp = (
            TO_NUMBER_HANDER[pattern.name](pattern, groupdict)
            for pattern in tree.patterns()
        )
        return double(coe, e, exp)


class IsPercent(GsheetNumAlike):
    # Spaces is not allowed between percent symbol and number

    DIGITS_NUMBER = (
        (DIGITS | IsIntegerE.DIGITS_E | IsFloat.DIGITS_FLOAT | IsFloatE.DIGITS_FLOAT_E)
        .named("digits_number")
        .group()
    )

    THOUSANDS_DIGITS_NUMBER = (
        (
            THOUSANDS_DIGITS
            | IsIntegerE.THOUSANDS_DIGITS_E
            | IsFloat.THOUSANDS_DIGITS_FLOAT
            | IsFloatE.THOUSANDS_DIGITS_FLOAT_E
        )
        .named("thousands_digits_number")
        .group()
    )

    PERCENT_NUMBER = (
        (DIGITS_NUMBER | THOUSANDS_DIGITS_NUMBER).named("percent_number").group()
    )

    # Combinations of percent position (before/after), number type (digit/thousand), number sign (empty/+/-/()), and whole sign (empty/+/-/()):
    # Total: 2 * 2 * 4 * 4 = 64 cases

    # 1. Cases with percent + optional sign + digit/thousand number + empty whole sign:
    #    Only the minus sign is allowed in these cases (8 cases: front * digit/thousand * (empty/-/+/()) * empty)
    # 2. Cases with optional sign 1 (empty/+/-/()) + percent + optional sign 2 + digit/thousand number:
    #    16 cases total: (empty/+/-/() * percent * empty/- * digit/thousand)
    # Note: The patterns (%-1), -%-1, +%-1, and %-1 are intentionally considered valid.
    PERCENT_MAYMINUS_NUMBER = (
        (PERCENT_SYMBOL + MINUS_MAYBE + PERCENT_NUMBER)
        .join(ANYSPACE)
        .named("percent_mayminus_number")
    ).group()
    SIGNED_PERCENT_MAYMINUS_NUMBER = MAY_SIGNED_NUMBER_WITH_CONDITIONAL_SPACING.format(
        num=PERCENT_MAYMINUS_NUMBER
    )

    # 15 invalid cases: -/+/() * digit/thousand * after * -/(),
    # 4 redundant cases where (empty * digit/thousand + after * -/+) == (-/+ digit/thousand * after * empty)
    # Case breakdown:
    # 2. Empty + digit + percent + whole sign (1 case: empty for whole sign)
    # 3. Empty + thousand + percent + whole sign (1 case: empty for whole sign)
    # 4. Empty + digit + percent + whole sign (3 cases: empty * digit * after * -/+/())
    # 5. Empty + thousand + percent + whole sign (3 cases: empty * thousand * after * -/+/())
    # 6. Sign + digit + percent + whole sign (1 case: () * digit * after * empty)
    # 7. Sign + thousand + percent + whole sign (1 case: () * thousand * after * empty)
    # 8. Sign + digit + percent + "+" as whole sign (3 cases: +/-/() * digit * after * +)

    UNSIGNED_THOUSANDS_DIGITS_NUMBER_PERCENT = (
        (THOUSANDS_DIGITS_NUMBER + PERCENT_SYMBOL)
        .named("unsigned_thousands_digits_number_percent")
        .group()
    )

    UNSIGNED_DIGITS_NUMBER_PERCENT = (
        (DIGITS_NUMBER + PERCENT_SYMBOL).named("unsigned_digits_number_percent").group()
    )

    # 2 & 3
    UNSIGNED_NUMBER_PERCENT = UNSIGNED_NUMBER_WITH_SPACES.format(
        num=(PERCENT_NUMBER + PERCENT_SYMBOL).named("unsigned_number_percent")
    )
    # 4
    WHOLE_SIGNED_DIGITS_NUMBER_PERCENT = MAY_SIGNED_NUMBER_WITH_SPACES.format(
        num=UNSIGNED_DIGITS_NUMBER_PERCENT
    )
    # 5
    WHOLE_SIGNED_THOUSANDS_DIGITS_NUMBER_PERCENT = (
        MAY_SIGNED_NUMBER_WITH_CONDITIONAL_SPACING.format(
            num=UNSIGNED_THOUSANDS_DIGITS_NUMBER_PERCENT
        )
    )
    # 6 & 7
    PARENTHESIS_NUMBER_PERCENT = UNSIGNED_NUMBER_WITH_SPACES.format(
        num=(PARENTHESIS_NUMBER.format(num=PERCENT_NUMBER) + PERCENT_SYMBOL)
        .named("parenthesis_number_percent")
        .group()
    )
    # 8
    PLUS_SIGNED_DIGITS_NUMBER_PERCENT = UNSIGNED_NUMBER_WITH_SPACES.format(
        num=(
            (PLUS + MAY_SIGNED_NUMBER.format(num=DIGITS_NUMBER) + PERCENT_SYMBOL)
            .join(ANYSPACE)
            .named("plus_signed_digits_number_percent")
            .group()
        )
    )

    NUMBER = (
        SIGNED_PERCENT_MAYMINUS_NUMBER
        | UNSIGNED_NUMBER_PERCENT
        | WHOLE_SIGNED_DIGITS_NUMBER_PERCENT
        | WHOLE_SIGNED_THOUSANDS_DIGITS_NUMBER_PERCENT
        | PARENTHESIS_NUMBER_PERCENT
        | PLUS_SIGNED_DIGITS_NUMBER_PERCENT
    ).named("percent")

    EXAMPLES = [
        "111%",
        "+111%",
        "-111%",
        "(111%)",
        "%111",
        " +%111",
        "-%111",
        "(%111)",
        " +111%",
        "++111%",
        "-111%",
        "+-111%",
        "%-111",
        " +%-111",
        "-%-111",
        "(%-111)",
        "(111)%",
        "+(111)%",
        "0,111,1111%",
        " +0,111,1111%",
        "-0,111,1111%",
        "(0,111,1111%)",
        "%0,111,1111",
        " +%0,111,1111",
        "-%0,111,1111",
        "(%0,111,1111)",
        " +0,111,1111%",
        "-0,111,1111%",
        "%-0,111,1111",
        " +%-0,111,1111",
        "-%-0,111,1111",
        "(%-0,111,1111)",
        "(0,111,1111)%",
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
    def percent_mayminus_number(
        tree: Composite, groupdict: dict[str, str]
    ) -> Optional[int | float]:
        if (ret := concat_sign(tree, groupdict)) is not None:
            return ret / 100
        return None

    @staticmethod
    def unsigned_thousands_digits_number_percent(
        tree: Composite, groupdict: dict[str, str]
    ) -> Optional[int | float]:
        return IsPercent._validate_percent(tree, groupdict)

    @staticmethod
    def unsigned_digits_number_percent(
        tree: Composite, groupdict: dict[str, str]
    ) -> Optional[int | float]:
        return IsPercent._validate_percent(tree, groupdict)

    @staticmethod
    def unsigned_number_percent(
        tree: Composite, groupdict: dict[str, str]
    ) -> Optional[int | float]:
        return IsPercent._validate_percent(tree, groupdict)

    @staticmethod
    def parenthesis_number_percent(
        tree: Composite, groupdict: dict[str, str]
    ) -> Optional[int | float]:
        return IsPercent._validate_percent(tree, groupdict)

    @staticmethod
    def plus_signed_digits_number_percent(
        tree: Composite, groupdict: dict[str, str]
    ) -> Optional[int | float]:
        return IsPercent._validate_percent(tree, groupdict)


class LeadingPercentageInconsistency(GsheetNumAlike, WeirdFeature):
    TYPE = "Weird"
    EXAMPLES = ["%111", "(%-11)", "%-11"]
    NUMBER = IsPercent.SIGNED_PERCENT_MAYMINUS_NUMBER


class IsCurrency(GsheetNumAlike):
    CURRENCY_NUMBER = (
        (
            DIGITS
            | IsIntegerE.DIGITS_E
            | IsFloat.DIGITS_FLOAT
            | IsFloatE.DIGITS_FLOAT_E
            | THOUSANDS_DIGITS
            | IsIntegerE.THOUSANDS_DIGITS_E
            | IsFloat.THOUSANDS_DIGITS_FLOAT
            | IsFloatE.THOUSANDS_DIGITS_FLOAT_E
        )
        .named("currency_number")
        .group()
    )

    CURRENCY_UNSIGNED_NUMBER = (
        (CURRENCY_SYMBOL + ANYSPACE + CURRENCY_NUMBER)
        .named("currency_unsigned_number")
        .group()
    )

    UNSIGNED_NUMBER_CURRENCY = (
        (CURRENCY_NUMBER + ANYSPACE + CURRENCY_SYMBOL)
        .named("unsigned_number_currency")
        .group()
    )

    UNSIGNED_NUMBER_GROUP = (
        (CURRENCY_UNSIGNED_NUMBER | UNSIGNED_NUMBER_CURRENCY)
        .named("unsigned_currency_group")
        .group()
    )

    # currency posion(before/after) * number sign(empty/+/-/()) * whole sign(empty/+/-/()) => 2 * 4 * 4 = 32 cases
    # before + … 16 cases, 7 valid cases:
    # 1. before + empty + empty/-/() (3 cases)
    # 2. before + empty + + (1 cases: requires at least one leading space)
    # 3. before + +/-/() + empty (3 cases)
    # after + … 16 cases, 7 valid cases, 1 redundant cases:
    # 4. after + empty + empty/-/() (3 cases)
    # 5. after + empty + + (1 cases: requires at least one leading space)
    # 6. after + -/() + empty (2 cases)

    # 1
    SIGNED_CURRENCY_UNSIGNED_NUMBER = (
        MAY_MINUS_NUMBER_SPACES.format(num=CURRENCY_UNSIGNED_NUMBER)
        | PARENTHESIS_NUMBER_SPACES.format(num=CURRENCY_UNSIGNED_NUMBER)
    ).named("signed_currency_unsigned_number")

    # 2 & 5
    PLUS_SIGNED_UNSIGNED_NUMBER_GROUP = (
        (
            # at least one leading space
            SPACE
            + PLUS
            + UNSIGNED_NUMBER_GROUP
        )
        .join_with_tail(ANYSPACE)
        .named("plus_signed_unsigned_number_group")
    )

    # 3
    UNSIGNED_CURRENCY_SIGNED_NUMBER = (
        (CURRENCY_SYMBOL + MAY_SIGNED_NUMBER_WITH_SPACES.format(num=CURRENCY_NUMBER))
        .join_with_head(ANYSPACE)
        .named("currency_signed_number")
    )

    # 4
    SIGNED_UNSIGNED_NUMBER_CURRENCY = (
        MAY_MINUS_NUMBER_SPACES.format(num=UNSIGNED_NUMBER_CURRENCY)
        | PARENTHESIS_NUMBER_SPACES.format(num=UNSIGNED_NUMBER_CURRENCY)
    ).named("signed_unsigned_number_currency")

    # 6
    UNSIGNED_SIGNED_NUMBER_CURRENCY = (
        MAY_MINUS_NUMBER_SPACES.format(num=UNSIGNED_NUMBER_CURRENCY)
        | (
            PARENTHESIS_NUMBER_SPACES.format(num=CURRENCY_NUMBER)
            + ANYSPACE
            + CURRENCY_SYMBOL
        ).named("parenthesis_number_currency")
    ).named("unsigned_signed_number_currency")

    NUMBER = (
        SIGNED_CURRENCY_UNSIGNED_NUMBER
        | PLUS_SIGNED_UNSIGNED_NUMBER_GROUP
        | UNSIGNED_CURRENCY_SIGNED_NUMBER
        | SIGNED_UNSIGNED_NUMBER_CURRENCY
        | UNSIGNED_SIGNED_NUMBER_CURRENCY
    ).named("currency")

    EXAMPLES = [
        rf"{CURRENCY_SYMBOL_EXAMPLE}111.222",
        rf" +{CURRENCY_SYMBOL_EXAMPLE}111.222",
        rf"-{CURRENCY_SYMBOL_EXAMPLE}111.222",
        rf"({CURRENCY_SYMBOL_EXAMPLE}111.222)",
        rf"{CURRENCY_SYMBOL_EXAMPLE}+111.222",
        rf"{CURRENCY_SYMBOL_EXAMPLE}-111.222",
        rf"{CURRENCY_SYMBOL_EXAMPLE}(111.222)",
        rf"{CURRENCY_SYMBOL_EXAMPLE}1,111",
        rf" +{CURRENCY_SYMBOL_EXAMPLE}1,111",
        rf"-{CURRENCY_SYMBOL_EXAMPLE}1,111",
        rf"({CURRENCY_SYMBOL_EXAMPLE}1,111)",
        rf"{CURRENCY_SYMBOL_EXAMPLE}+1,111",
        rf"{CURRENCY_SYMBOL_EXAMPLE}-1,111",
        rf"{CURRENCY_SYMBOL_EXAMPLE}(1,111)",
        rf"111.222{CURRENCY_SYMBOL_EXAMPLE}",
        rf" +111.222{CURRENCY_SYMBOL_EXAMPLE}",
        rf"-111.222{CURRENCY_SYMBOL_EXAMPLE}",
        rf"(111.222{CURRENCY_SYMBOL_EXAMPLE})",
        rf"-111.222{CURRENCY_SYMBOL_EXAMPLE}",
        rf"(111.222){CURRENCY_SYMBOL_EXAMPLE}",
        rf"1,111{CURRENCY_SYMBOL_EXAMPLE}",
        rf" +1,111{CURRENCY_SYMBOL_EXAMPLE}",
        rf"-1,111{CURRENCY_SYMBOL_EXAMPLE}",
        rf"(1,111{CURRENCY_SYMBOL_EXAMPLE})",
        rf"-1,111{CURRENCY_SYMBOL_EXAMPLE}",
        rf"(1,111){CURRENCY_SYMBOL_EXAMPLE}",
    ]

    @staticmethod
    def currency_symbol(_node: Primitive, _groupdict: dict[str, str]) -> str:
        return ""


@register
def digits(node: Primitive, groupdict: dict[str, str]) -> Optional[int | float]:
    digits = groupdict[node.uid]
    if int(digits) == 0:
        return 0
    digits = digits.lstrip("0")
    # Handle known quirks. This is an empirical list of string patterns
    # that trigger aggressive, non-intuitive rounding
    exceptions = [
        "999999999999998",
        "999999999999999",
        "99999999999999600",
        "99999999999999700",
    ]
    for i in exceptions:
        if i in digits:
            return float("1" + "0" * len(digits))
    # GSheet's main filter: count significant digits. If <= 15, the number
    # is considered "safe" and is converted to a float.
    if len(digits.strip("0")) <= 15:
        return int(digits) if len(digits) <= 15 else float(digits)
    return None


@register
def int_digits(node: Primitive, groupdict: dict[str, str]) -> int:
    if (ret := digits(node, groupdict)) is not None:
        return int(ret)
    return None


@register
def thousands_digits(node: Primitive, groupdict: dict[str, str]) -> int | float:
    """Convert the thousands digits to an integer using the python tokenizer."""
    return truncate_to_15_with_zeros(groupdict[node.uid].replace(",", ""))


@register
def int_thousands_digits(node: Primitive, groupdict: dict[str, str]) -> int:
    if (ret := thousands_digits(node, groupdict)) is not None:
        return int(ret)
    return None


@register("sign", "plus", "minus", "exponent", "dot")
def primitive(node: Primitive, groupdict: dict[str, str]) -> str:
    return groupdict[node.uid]


@register(
    "may_sign_number_spaces",
    "plus_number_spaces",
    "may_minus_number_spaces",
    "may_signed_number_",
)
def sign_handler(tree: Composite, groupdict: dict[str, str]) -> Optional[float | int]:
    return concat_sign(tree, groupdict)


@register("parenthesis_number", "parenthesis_number_spaces")
def parenthesis_number(
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
