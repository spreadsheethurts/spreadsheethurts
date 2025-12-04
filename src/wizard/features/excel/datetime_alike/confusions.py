from typing import Optional

from wizard.feature import WeirdFeature
from .utils import DateTimeUtils
from wizard.features.common.pattern import Primitive, String


util = DateTimeUtils()


class MakeNoSense(WeirdFeature):
    """A base class for patterns with nonsensical but inferable rules."""

    @staticmethod
    def clean_groupdict(groupdict: dict[str, Optional[str]]):
        """Remove None values from a groupdict and return a dict."""
        result = {}
        for k, v in groupdict.items():
            if v is None:
                continue
            key = k.rsplit("_", 1)[0]  # Split on last '_' and take first part
            if key in result:
                raise ValueError(f"Duplicate key found: {key}")
            result[key] = v
        return result

    @classmethod
    def fullmatch(cls, content: str) -> Optional[dict]:
        if not cls.PATTERN:
            return None

        if match := cls.PATTERN.fullmatch(content):
            return cls.clean_groupdict(match.groupdict())

        return None


class MonthNameColon(MakeNoSense):

    PATTERN = (
        (Primitive.letters().named("month") + String.colon())
        .join_with_tail(String.anyspace())
        .compile()
    )

    @classmethod
    def evaluate(cls, s: str) -> bool:
        if (match := cls.fullmatch(s)) and (month := match.get("month")):
            return util.get_month(month) is not None
        return False


class MonthNameInteger(MakeNoSense):
    MONTH_GROUP = "month"
    INTEGER_GROUP = "integer"

    @classmethod
    def is_integer_group_valid(cls, digit: str) -> bool:
        """Check if the integer is within a valid range."""
        if int(digit) == 0 and util.is_zero_valid(digit):
            return True
        elif digit.startswith("0"):
            return False

        return 0 <= int(digit) <= 59

    @classmethod
    def evaluate(cls, s: str) -> bool:
        if match := cls.fullmatch(s):
            month, integer = match.get(cls.MONTH_GROUP), match.get(cls.INTEGER_GROUP)

            if util.get_month(month) and cls.is_integer_group_valid(integer):
                return True

        return False


class MonthNameColonInteger(MonthNameInteger):
    """Matches a pattern consisting of a month name followed by a colon and an integer within the range of 0-59."""

    EXAMPLES = ["Jan: 1", "Jan: 59", "Jan: 0"]
    COUNTER_EXAMPLES = ["Ja: 60", "Jan: 65"]

    # The 'dot' option is added to this pattern instead of 'MonthNameColonDecimal' because the calculation result of formula "add" is more consistent with other patterns.

    PATTERN = (
        (
            Primitive.letters().named(MonthNameInteger.MONTH_GROUP)
            + String.colon()
            + Primitive.digits().named(MonthNameInteger.INTEGER_GROUP)
            + (String.dot() | String.hyphen() | String.colon() | String.slash())
            .group()
            .maybe()
        )
        .join_with_tail(String.anyspace())
        .compile()
    )


class MonthNameColonDecimal(MonthNameInteger):
    """Matches a pattern that consists of a month name followed by a colon and a decimal, where the whole number part of the decimal falls within the range of 0-59."""

    EXAMPLES = ["Jan: 1.0", "Jan: 59.0", "Jan: 0.0", "Jan: 0.1", "Jan: 0.99999999"]
    COUNTER_EXAMPLES = ["Ja: 60.0", "Ja: 33.0"]

    PATTERN = (
        (
            Primitive.letters().named(MonthNameInteger.MONTH_GROUP)
            + String.colon()
            + Primitive.digits().named(MonthNameInteger.INTEGER_GROUP)
            + String.dot()
            + String.digits()
            # Dot is invalid here
            + (String.hyphen() | String.colon() | String.slash()).group().maybe()
        )
        .join_with_tail(String.anyspace())
        .compile()
    )


class IntegerColonMonthName(MonthNameInteger):
    """Matches a pattern consisting of an integer (within the range 0-23) followed by a colon and a month name."""

    EXAMPLES = ["1: Jan", "23: Jan", "0: Jan"]
    COUNTER_EXAMPLES = ["24: Jan", "25: Ja"]

    PATTERN = (
        (
            Primitive.digits().named(MonthNameInteger.INTEGER_GROUP)
            + String.colon()
            + Primitive.letters().named(MonthNameInteger.MONTH_GROUP)
        )
        .join_with_tail(String.anyspace())
        .compile()
    )

    @classmethod
    def is_integer_group_valid(cls, digit: str) -> bool:
        if int(digit) == 0 and util.is_zero_valid(digit):
            return True
        elif digit.startswith("0"):
            return False
        return 0 <= int(digit) <= 23


class IntegerColonMonthNameDotInteger(MakeNoSense):
    """Matches a pattern consisting of an integer (within the range 0-59) followed by a colon, a month name, a dot, and another integer."""

    EXAMPLES = ["1: Jan. 0", "59: Jan. 0", "11: Jan. 9999"]
    COUNTER_EXAMPLES = ["60: Jan. 0", "0: Ja . 0"]

    INTEGER_GROUP = "integer"
    MONTH_GROUP = "month"

    PATTERN = (
        (
            Primitive.digits().named(INTEGER_GROUP)
            + String.colon()
            + Primitive.letters().named(MONTH_GROUP)
            + String.dot()
            + Primitive.digits()
        )
        .join_with_tail(String.anyspace())
        .compile()
    )

    @classmethod
    def evaluate(cls, s: str) -> bool:
        if match := cls.fullmatch(s):
            integer: str = match.get(cls.INTEGER_GROUP)
            month = match.get(cls.MONTH_GROUP)

            if util.get_month(month):
                # Leading zeros (except "0" or "00") are not allowed
                if int(integer) == 0 and util.is_zero_valid(integer):
                    return True
                elif integer.startswith("0"):
                    return False

                if 0 <= int(integer) <= 59:
                    return True

        return False


class MonthNameColonIntegerColonDecimal(MakeNoSense):
    EXAMPLES = ["Jan: 1: 0.0"]
    MONTH = "month"
    WHOLE = "whole"
    FRACTION = "fraction"
    INTEGER = "integer"

    PATTERN = (
        (
            Primitive.letters().named(MONTH)
            + String.colon()
            + Primitive.digits().named(INTEGER)
            + String.colon()
            + Primitive.digits().named(WHOLE)
            + String.dot()
            + Primitive.digits().named(FRACTION)
            # Dot is invalid here
            + (String.hyphen() | String.colon() | String.slash()).group().maybe()
        )
        .join_with_tail(String.anyspace())
        .compile()
    )

    @classmethod
    def evaluate(cls, s: str) -> bool:
        if match := cls.fullmatch(s):
            month, integer, whole = (
                match.get(cls.MONTH),
                match.get(cls.INTEGER),
                match.get(cls.WHOLE),
            )

            # The fraction accommodates all possible digits
            if (
                util.get_month(month)
                and util.validate_digit_within_bounds(integer, 0, 59)
                and util.validate_digit_within_bounds(whole, 0, 59)
            ):
                return True
        return False


class MonthNameColonDecimalColonInteger(MakeNoSense):
    EXAMPLES = ["Jan: 0.0: 0"]
    MONTH_GROUP = "month"
    WHOLE = "whole"
    FRACTION = "fraction"
    INTEGER = "integer"

    PATTERN = (
        (
            Primitive.letters().named(MONTH_GROUP)
            + String.colon()
            + Primitive.digits().named(WHOLE)
            + String.dot()
            + Primitive.digits().named(FRACTION)
            + String.colon()
            + Primitive.digits().named(INTEGER)
            # Dot is invalid here
            + (String.hyphen() | String.colon() | String.slash()).group().maybe()
        )
        .join_with_tail(String.anyspace())
        .compile()
    )

    @classmethod
    def evaluate(cls, s: str) -> bool:
        if match := cls.fullmatch(s):
            month, whole, fraction, integer = (
                match.get(cls.MONTH_GROUP),
                match.get(cls.WHOLE),
                match.get(cls.FRACTION),
                match.get(cls.INTEGER),
            )

            if (
                util.get_month(month)
                and util.validate_digit_within_bounds(whole, 0, 59)
                and util.validate_digit_within_bounds(fraction, 0, 59)
                and util.validate_digit_within_bounds(integer, 0, 9999)
            ):
                return True
        return False


class MonthNameColonIntegerColonInteger(MakeNoSense):
    EXAMPLES = ["Jan: 0: 0"]
    MONTH_GROUP = "month"
    INTEGER1 = "integer1"
    INTEGER2 = "integer2"

    PATTERN = (
        (
            Primitive.letters().named(MONTH_GROUP)
            + String.colon()
            + Primitive.digits().named(INTEGER1)
            + String.colon()
            + Primitive.digits().named(INTEGER2)
            + (String.dot() | String.hyphen() | String.colon() | String.slash())
            .group()
            .maybe()
        )
        .join_with_tail(String.anyspace())
        .compile()
    )

    @classmethod
    def evaluate(cls, s: str) -> bool:
        if match := cls.fullmatch(s):
            month, integer1, integer2 = (
                match.get(cls.MONTH_GROUP),
                match.get(cls.INTEGER1),
                match.get(cls.INTEGER2),
            )

            if (
                util.get_month(month)
                and util.validate_digit_within_bounds(integer1, 0, 59)
                and util.validate_digit_within_bounds(integer2, 0, 59)
            ):
                return True
        return False
