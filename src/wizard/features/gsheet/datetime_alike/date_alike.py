from typing import Optional
from datetime import date
from calendar import monthrange

from wizard.features.common.datetime_alike.datetime import DatetimeDict

from ...common.pattern import Primitive, Placeholder
from .utils import DateTimeUtils

from wizard.typ import GsheetDateTime
from .base import GsheetDateTimeAlikeBase, DateDict

utils = DateTimeUtils()

COMMA = Primitive.comma()
ANYSPACE = Primitive.anyspace()
SOMESPACE = Primitive.somespace()


MONTHNAME_DIGIT_SEP = (
    (ANYSPACE + (Primitive.slash() | Primitive.hyphen()) + ANYSPACE).group()
    | Primitive.somespace()
    | (Primitive.anyspace() + Primitive.dot() + Primitive.somespace()).group()
    | (COMMA + ANYSPACE).group()
    | (ANYSPACE + COMMA).group()
    | Primitive.empty()
).group()

DIGIT_DIGIT_SEP = (
    Primitive.slash()
    | Primitive.hyphen()
    | Primitive.somespace()
    | (Primitive.anyspace() + Primitive.dot() + Primitive.somespace()).group()
    | (COMMA + SOMESPACE).group()
    | (SOMESPACE + COMMA).group()
).group()

DIGIT_DIGIT_SEP_WITHOUT_HYPHEN = (
    Primitive.slash()
    | Primitive.somespace()
    | (Primitive.anyspace() + Primitive.dot() + Primitive.somespace()).group()
    | (COMMA + SOMESPACE).group()
    | (SOMESPACE + COMMA).group()
).group()

NAMED_DAY = Primitive.digits().named("day")
NAMED_MONTH_NUMBER = Primitive.digits().named("month")
NAMED_MONTH_LETTER = Primitive.letters().named("month")
NAMED_YEAR = Primitive.digits().named("year")
NAMED_DIGIT_DIGIT_SEP = DIGIT_DIGIT_SEP.named("sep")
NAMED_MONTHNAME_DIGIT_SEP = MONTHNAME_DIGIT_SEP.named("sep")
NAMED_DAY_OF_WEEK = Primitive.letters().named("day_of_week")

WITH_DAY_OF_WEEK = (
    ANYSPACE + Placeholder("date") + NAMED_DAY_OF_WEEK.maybe() + ANYSPACE
) | (
    (ANYSPACE + NAMED_DAY_OF_WEEK + Primitive.comma().maybe() + Primitive.somespace())
    .maybe()
    .group()
    + Placeholder("date")
)


class DateAlike(GsheetDateTimeAlikeBase):
    @classmethod
    def is_datetime_valid(cls, **kwargs: DateDict) -> Optional[GsheetDateTime]:
        day_of_week, year, month, day = (
            kwargs.get("day_of_week", None),
            kwargs.get("year", date.today().year),
            kwargs.get("month", 1),
            kwargs.get("day", 1),
        )

        day_of_week, year, month, day = (
            utils.get_day_of_week(day_of_week),
            utils.get_year(year),
            utils.get_month(month),
            utils.get_day(day),
        )
        if not day_of_week:
            return None

        if not (year and month and day):
            return None

        try:
            return GsheetDateTime(year, month, day)
        except ValueError:
            return None


class TripleDigits(DateAlike):

    TEMPLATE = (
        (
            Placeholder("digits1")
            + NAMED_DIGIT_DIGIT_SEP
            + Placeholder("digits2")
            + NAMED_DIGIT_DIGIT_SEP.backref()
            + Placeholder("digits3")
        )
        .clone()
        .surround_anyspace()
        # Backreferences above enforce an exact separator match, with an exception:
        # one sep must be an optional comma followed by somespace, while the other can be either a comma followed by anyspace or somespace.
        | (
            Placeholder("digits1")
            + (COMMA.maybe() + SOMESPACE).group()
            + Placeholder("digits2")
            + ((COMMA + ANYSPACE) | SOMESPACE).group()
            + Placeholder("digits3")
        ).surround_anyspace()
        | (
            Placeholder("digits1")
            + ((COMMA + ANYSPACE) | SOMESPACE).group()
            + Placeholder("digits2")
            + (COMMA.maybe() + SOMESPACE).group()
            + Placeholder("digits3")
        ).surround_anyspace()
    )


class MonthNumberDayYear(TripleDigits):
    EXAMPLES = [
        "1/1/2021",
        "1-1-2021",
        "12. 1. 2021",
        "2, 29  2000",
        "12 . 1 . 2025",
        "sun, 12. 1. 2025",
        "Mon 1/1/2021",
        "2, 29 2000 FRi",
    ]
    COUNTER_EXAMPLES = ["13/1/202"]

    PATTERN = (
        WITH_DAY_OF_WEEK.format(
            date=(
                TripleDigits.TEMPLATE.format(
                    digits1=NAMED_MONTH_NUMBER, digits2=NAMED_DAY, digits3=NAMED_YEAR
                )
            )
        )
        .clone()
        .compile()
    )


class YearMonthNumberDay(TripleDigits):
    # The two separator should be identical.
    EXAMPLES = [
        "2021-1-1",
        "100-1-1",
        "099/1/1",
        "001  1 1",
        "2021. 1. 1",
        "2021 . 1 . 1",
        "2021, 1, 1",
        "2021 1, 1",
        "099, 1 1",
        "sun, 2021-1-1",
        "Mon 2021-1-1",
        "2021-1-1 fri",
    ]
    COUNTER_EXAMPLES = ["2021-1/1", "99-1-1", "1, 1, 1", "32/1/1"]
    PATTERN = (
        WITH_DAY_OF_WEEK.format(
            date=TripleDigits.TEMPLATE.format(
                digits1=NAMED_YEAR, digits2=NAMED_MONTH_NUMBER, digits3=NAMED_DAY
            )
        ).clone()
    ).compile()

    @classmethod
    def validate(cls, groupdict: DatetimeDict) -> Optional[DatetimeDict]:
        # Year must have 3 or more digits or year is 0
        if len(groupdict["year"]) >= 3 or groupdict["year"] == "0":
            return groupdict
        return None


class DoubleDigits(DateAlike):
    TEMPLATE = (
        Placeholder("digits1") + DIGIT_DIGIT_SEP + Placeholder("digits2")
    ).surround_anyspace()


class MonthNumberDay(DoubleDigits):
    EXAMPLES = ["1/1", "1-1", "1. 1", "1  1", "1 . 1", "thu, 1 1"]
    PATTERN = (
        WITH_DAY_OF_WEEK.format(
            date=DoubleDigits.TEMPLATE.format(
                digits1=NAMED_MONTH_NUMBER, digits2=NAMED_DAY
            )
        )
        .clone()
        .compile()
    )


class MonthNumberYear(DoubleDigits):
    EXAMPLES = ["1/0100", "1-0999", "1. 0001", "1  9999", "1 . 0010", "Thu 1/0100"]
    COUNTER_EXAMPLES = ["1/1", "1-33", "1. 100"]
    PATTERN = (
        WITH_DAY_OF_WEEK.format(
            date=DoubleDigits.TEMPLATE.format(
                digits1=NAMED_MONTH_NUMBER, digits2=NAMED_YEAR
            )
        )
        .clone()
        .compile()
    )

    @classmethod
    def validate(cls, groupdict: DatetimeDict) -> Optional[DatetimeDict]:
        # The year is exactly 4 digits.
        year = groupdict["year"]
        if len(year) == 4:
            return groupdict
        return None


class YearMonthNumber(DoubleDigits):
    EXAMPLES = ["0100/1", "0999-1", "0001. 1", "9999  1", "0010 . 1", "sat 0100/1"]
    PATTERN = (
        WITH_DAY_OF_WEEK.format(
            date=DoubleDigits.TEMPLATE.format(
                digits1=NAMED_YEAR, digits2=NAMED_MONTH_NUMBER
            )
        )
        .clone()
        .compile()
    )

    @classmethod
    def validate(cls, groupdict: DatetimeDict) -> Optional[DatetimeDict]:
        # The year is exactly 4 digits.
        year = groupdict["year"]
        if len(year) == 4:
            return groupdict
        return None


class MonthNameDigit(DateAlike):
    # The comma must touch either the month name or the digit.
    TEMPLATE = (
        (NAMED_MONTH_LETTER + MONTHNAME_DIGIT_SEP).group() + Placeholder("num")
    ).join_both_ends(ANYSPACE)


class MonthNameDay(MonthNameDigit):
    EXAMPLES = [
        "May. 1",
        "Jan 1",
        "Feb . 1",
        "Jan1",
        "january - 1",
        "Jun ,1",
        "Jan, 1",
        "Jan- 1",
        "Jan / 1",
        "June-1",
        "sun, May. 1",
        "Mon Jan 1",
        "Jun 1 fri",
    ]
    COUNTER_EXAMPLES = ["Jan , 1"]
    PATTERN = (
        WITH_DAY_OF_WEEK.format(date=MonthNameDigit.TEMPLATE.format(num=NAMED_DAY))
        .clone()
        .compile()
    )


class MonthNameYear(MonthNameDigit):
    EXAMPLES = [
        "May. 0100",
        "Jan 0999",
        "Feb . 0001",
        "Jan 9999",
        "january - 0010",
        "fri May. 0100",
    ]
    COUNTER_EXAMPLES = ["May. 1", "Jan 33", "Feb . 999", "Feb , 1000"]
    PATTERN = (
        WITH_DAY_OF_WEEK.format(date=MonthNameDigit.TEMPLATE.format(num=NAMED_YEAR))
        .clone()
        .compile()
    )

    @classmethod
    def validate(cls, groupdict: DatetimeDict) -> Optional[DatetimeDict]:
        # The year is exactly 4 digits.
        year = groupdict["year"]
        if len(year) == 4:
            return groupdict
        return None


class DigitMonthName(DateAlike):
    TEMPLATE = (
        Placeholder("num") + MONTHNAME_DIGIT_SEP + NAMED_MONTH_LETTER
    ).join_both_ends(ANYSPACE)


class DayMonthName(DigitMonthName):
    EXAMPLES = [
        "1. May",
        "1 jan",
        "1-feb",
        "1 january",
        "1/oct",
        "1 - january",
        "1Jan",
        "Mon 1 Jan",
        "1 Jan Fri",
    ]
    PATTERN = (
        WITH_DAY_OF_WEEK.format(date=DigitMonthName.TEMPLATE.format(num=NAMED_DAY))
        .clone()
        .compile()
    )


class YearMonthName(DigitMonthName):
    EXAMPLES = ["2021. May", "0019 jan", "Mon 2021 May", "2021 May Fri"]
    COUNTER_EXAMPLES = ["202. May", "009 jan"]
    PATTERN = (
        WITH_DAY_OF_WEEK.format(date=DigitMonthName.TEMPLATE.format(num=NAMED_YEAR))
        .clone()
        .compile()
    )

    @classmethod
    def validate(cls, groupdict: DatetimeDict) -> Optional[DatetimeDict]:
        # The year is exactly 4 digits.
        year = groupdict["year"]
        if len(year) == 4:
            return groupdict
        return None


class DigitMonthNameDigit(DateAlike):
    # The two separators can be different.
    TEMPLATE = (
        (
            Placeholder("digit1")
            + MONTHNAME_DIGIT_SEP
            + NAMED_MONTH_LETTER
            + MONTHNAME_DIGIT_SEP
            + Placeholder("digit2")
        )
        .clone()
        .surround_anyspace()
    )


# DayMonthNameYear has higher priority than YearMonthNameDay.
class DayMonthNameYear(DigitMonthNameDigit):
    EXAMPLES = ["1. May 999", "2 jan 1", "3-feb 100", "1 january 9999", "1/oct 0001"]

    PATTERN = (
        WITH_DAY_OF_WEEK.format(
            date=DigitMonthNameDigit.TEMPLATE.format(
                digit1=NAMED_DAY, digit2=NAMED_YEAR
            )
        )
        .clone()
        .compile()
    )


class YearMonthNameDay(DigitMonthNameDigit):
    EXAMPLES = ["32Jan. 1", "2001-Jan/1", "30feb, 1", "99999Jan1", "fri 99999Jan1"]
    COUNTER_EXAMPLES = ["31Jan. 1", "1-Jan/1"]

    PATTERN = (
        WITH_DAY_OF_WEEK.format(
            date=DigitMonthNameDigit.TEMPLATE.format(
                digit1=NAMED_YEAR, digit2=NAMED_DAY
            )
        )
        .clone()
        .compile()
    )

    @classmethod
    def validate(cls, groupdict: DatetimeDict) -> Optional[DatetimeDict]:
        if month := utils.get_month(groupdict["month"]):
            current_year = date.today().year
            _, max_day = monthrange(current_year, month)
            # Note: This is intentional - we verify whether the year value could represent a valid day
            if day := utils.get_day(groupdict["year"]):
                if 1 <= day <= max_day:
                    return None

        return groupdict


class MonthNameDayYear(DateAlike):
    EXAMPLES = [
        "Jan, 1 2021",
        "Jan 1, 2021",
        "Jan-1/0019",
        "mar -1-2001",
        "FeB /1,2021",
    ]

    PATTERN = (
        WITH_DAY_OF_WEEK.format(
            date=(
                (
                    NAMED_MONTH_LETTER
                    + MONTHNAME_DIGIT_SEP
                    + NAMED_DAY
                    + (DIGIT_DIGIT_SEP_WITHOUT_HYPHEN | COMMA).group()
                    + NAMED_YEAR
                ).surround_anyspace()
                | (
                    # A hyphen can only be used as a second separator if the first separator is also a hyphen.
                    NAMED_MONTH_LETTER
                    + (ANYSPACE + Primitive.hyphen() + ANYSPACE).group()
                    + NAMED_DAY
                    + Primitive.hyphen()
                    + NAMED_YEAR
                )
                .clone()
                .surround_anyspace()
            )
        )
        .clone()
        .compile()
    )
