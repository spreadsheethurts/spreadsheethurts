from wizard.feature import WeirdFeature
from ...common.pattern import Primitive, String, Placeholder

SIGN = Primitive("[+-]").named("sign")
ANYSPACE = String.anyspace()

MAYSIGN_NUMBER_SPACES = (SIGN.maybe() + Placeholder("num")).join_both_ends(ANYSPACE)
NUMBER_MAYSIGN_SPACES = (
    (Placeholder("num") + SIGN.maybe()).clone().join_both_ends(ANYSPACE)
)
PARENTHESIS_NUMBER_SPACES = (String(r"\(") + Placeholder("num") + r"\)").join_both_ends(
    ANYSPACE
)

MAY_SIGNED_NUMBER = (
    MAYSIGN_NUMBER_SPACES | NUMBER_MAYSIGN_SPACES | PARENTHESIS_NUMBER_SPACES
)

PERCENT_SYMBOL = String("%")
CURRENCY_SYMBOL = String(r"\$")
CURRENCY_SYMBOL_EXAMPLE = "$"


class ConfusedNumAlike(WeirdFeature):
    @classmethod
    def evaluate(cls, s: str) -> bool:
        return cls.PATTERN.fullmatch(s) is not None


class HybridCommaDotSeparatedInteger(ConfusedNumAlike):
    """Matches numbers where both dot and comma are used as decimal separators (e.g. 123.45667,333,333).

    Within the 15 digit precision:
    1. Calc treats the last comma as decimal separator:  "1.2,333,444" -> "1.2,333.444"
    2. Removes other commas and decimal points:          "1.2,333.444" -> "12333.444"
    3. Then a valid decimal number is formed:            "12333.444"
    """

    EXAMPLES = ["22.44,333", "123.45667,789", "123.45667,789,123", "22.33,333+"]

    COMMA_DIGITS_REPEAT = (String.comma() + Primitive.digit().repeat(3)).some().group()
    HYBRID_THOUSANDS_NOTATION = (
        Primitive.digits() + String.dot() + Primitive.digits() + COMMA_DIGITS_REPEAT
    ).group()
    PATTERN = MAY_SIGNED_NUMBER.format(num=(HYBRID_THOUSANDS_NOTATION)).compile()

    @classmethod
    def evaluate(cls, s: str) -> bool:
        return cls.PATTERN.fullmatch(s) is not None


class HybridCommaDotSeparatedIntegerE(ConfusedNumAlike):
    EXAMPLES = ["22.44,333e-1", "1.2,333,444e1"]

    MAY_SIGNED_DIGITS = (SIGN.maybe() + Primitive.digits()).group()
    INTEGER_E = (
        HybridCommaDotSeparatedInteger.HYBRID_THOUSANDS_NOTATION
        + Primitive.exponent()
        + MAY_SIGNED_DIGITS
    ).group()

    PATTERN = MAY_SIGNED_NUMBER.format(num=INTEGER_E).clone().compile()


class HybridCommaDotSeparatedPercent(ConfusedNumAlike):
    EXAMPLES = ["1.2,333,444%", "(1.2,333,444)%", "-1.2,333,444%", "1.2,333,444-%"]

    PATTERN = (
        (
            MAY_SIGNED_NUMBER.format(
                num=HybridCommaDotSeparatedInteger.HYBRID_THOUSANDS_NOTATION
            )
            + PERCENT_SYMBOL
        )
        .join_both_ends(ANYSPACE)
        .clone()
        .compile()
    )


class HybridCommaDotSeparatedCurrency(ConfusedNumAlike):
    EXAMPLES = [
        f"{CURRENCY_SYMBOL_EXAMPLE}1.2,333,444",
        f"{CURRENCY_SYMBOL_EXAMPLE}-1.2,333,444",
        f"{CURRENCY_SYMBOL_EXAMPLE}(1.2,333,444)",
        f"{CURRENCY_SYMBOL_EXAMPLE}+1.2,333,444",
        f"{CURRENCY_SYMBOL_EXAMPLE}1.2,333,444-",
        f"1.2,333,444{CURRENCY_SYMBOL_EXAMPLE}",
        f"-1.2,333,444{CURRENCY_SYMBOL_EXAMPLE}",
        f"(1.2,333,444){CURRENCY_SYMBOL_EXAMPLE}",
        f"1.2,333,444-{CURRENCY_SYMBOL_EXAMPLE}",
    ]

    PATTERN = (
        (
            (
                CURRENCY_SYMBOL
                + MAY_SIGNED_NUMBER.format(
                    num=HybridCommaDotSeparatedInteger.HYBRID_THOUSANDS_NOTATION
                )
            ).join(ANYSPACE)
            | (
                MAY_SIGNED_NUMBER.format(
                    num=HybridCommaDotSeparatedInteger.HYBRID_THOUSANDS_NOTATION
                )
                + CURRENCY_SYMBOL
            ).join(ANYSPACE)
            | PARENTHESIS_NUMBER_SPACES.format(
                num=HybridCommaDotSeparatedInteger.HYBRID_THOUSANDS_NOTATION
                + ANYSPACE
                + CURRENCY_SYMBOL
            )
        )
        .clone()
        .compile()
    )


class OmitSlashPart(ConfusedNumAlike):
    """Matches numbers with the pattern: digits, three digits after comma, followed by slash and more digits.

    Calc treats ',' as a thousands separator, allowing only one group of three digits.
    Any digits after the slash are omitted from the calculation, and Calc automatically formats the number as a fraction.

    For example:
    "22,333/44" -> "22333" (omits "/44", automatically formatted as fraction by Calc)
    "000222,333/333" -> "222333" (omits "/333", automatically formatted as fraction by Calc)
    """

    EXAMPLES = ["22,333/44", "000222,333/333"]

    PATTERN = (
        (MAYSIGN_NUMBER_SPACES | NUMBER_MAYSIGN_SPACES)
        .format(
            num=(
                Primitive.digits()
                + String.comma()
                + Primitive.digit().repeat(3)
                + String.slash()
                + Primitive.digits()
            )
        )
        .compile()
    )


class Exponent(ConfusedNumAlike):
    """Matches numbers where the exponent symbol is followed by an addition or subtraction expression (e.g. 22,333.E11-44).

    For example, in "22,333.E11-44":
    1. "22,333" is treated as the integer part
    2. "11" after 'E' is treated as the decimal part
    3. "44" provides the exponent
    4. The "-" sign is treated as negating the entire number, rather than the exponent
    5. The final number is interpreted as -22,333.11e44 -> -2.233311e+48
    """

    EXAMPLES = ["22,333.E11-44", "22,333,333.E10+3"]
    # Note: The sign is the sign of the whole number, not the exponent.
    COMMA_DIGITS_REPEAT = (String.comma() + Primitive.digit().repeat(3)).some().group()
    PATTERN = (
        (
            Primitive.digits()
            + COMMA_DIGITS_REPEAT
            + String.dot()
            + Primitive.exponent()
            + Primitive.digits()
            + SIGN
            + Primitive.digits()
        )
        .surround_anyspace()
        .compile()
    )
