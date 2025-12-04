from typing import Optional
from datetime import date
from .utils import DateTimeUtils

from .base import ExcelDateTimeAlikeBase, DateDict
from ...common.pattern import Primitive, Placeholder
from wizard.typ import ExcelDateTime

util = DateTimeUtils()

EMPTY = Primitive.empty()
COMMA = Primitive.comma()
DASH = Primitive.hyphen()
SLASH = Primitive.slash()
SEP = DASH | SLASH
SPACE = Primitive.space()
ANYSPACE = Primitive.anyspace()
SOMESPACE = Primitive.somespace()


NAMED_YEAR = Primitive.digits().named("year")
NAMED_MONTH_NUMBER = Primitive.digits().named("month")
NAMED_MONTH_LETTER = Primitive.letters().named("month")
NAMED_DAY = Primitive.digits().named("day")


class DateAlike(ExcelDateTimeAlikeBase):
    """This class serves as the base for all date-like features.

    It provides functionality to match and validate date-like patterns within a cell's content.
    """

    @classmethod
    def is_datetime_valid(
        cls,
        **kwargs: DateDict,
    ) -> Optional[ExcelDateTime]:
        year, month, day = (
            kwargs.get("year", date.today().year),
            kwargs.get("month", 1),
            kwargs.get("day", 1),
        )
        """Verify if the date is valid.

        If the year is one or two digit and is less than 30(configurable), the year is converted to a 20xx format,
        representing the current century. Otherwise, it is converted to a 19xx format, representing the previous century.

        Args:
            year: The year of the date. Defaults to the current year.
            month: The month of the date. Defaults to 1 (January).
            day: The day of the date. Defaults to 1.

        Returns:
            The date if it is valid, otherwise None.
        """
        year, month, day = (
            util.get_year(year),
            util.get_month(month),
            util.get_day(day),
        )
        if not (year and month and day):
            return None

        try:
            return ExcelDateTime(year, month, day)
        except ValueError:
            return None


class DayMonthName(DateAlike):
    """Match a date with the format '1 June', '1 - Jun', '1 / Jun', '1JUN'."""

    EXAMPLES = [
        "1 June",
        "1 - Jun",
        "1 / Jun",
        "1JUN",
    ]

    PATTERN = (
        (NAMED_DAY + (SEP | SPACE.maybe()) + NAMED_MONTH_LETTER)
        .join_with_tail(ANYSPACE)
        .compile()
    )


# MonthNumberDay and DayMonthNumber can capture the same pattern,
# such as '5/4'. However, ensure that A has higher precedence.
# With this precedence, '5/4' represents March 4th, not April 5th.


class NumberSepNumber(DateAlike):
    # Based on experimental findings, the numeric value following the separator is identified as either the day or the month.
    # Consequently, a broader range of 1-31 is utilized to accommodate all potential values within this context, rather than
    # considering the entire spectrum of numbers.

    TEMPLATE = (Placeholder("first") + SEP + Placeholder("second")).join_with_tail(
        ANYSPACE
    )


# MonthNumberDay > DayMonthNumber > YearMonthNumber
class YearMonthNumber(NumberSepNumber):
    """
    Match a date formatted with either a two-digit year or a four-digit year followed by the month,
    exemplified by '41 / 3', '32 / 4'.

    The month must be valid, and the year's value should exceed the month's maximum number of days.
    When the year is provided as two digits, it is converted into a four-digit year by prefixing it
    with the century immediately preceding the current one.
    """

    PATTERN = NumberSepNumber.TEMPLATE.format(
        first=NAMED_YEAR, second=NAMED_MONTH_NUMBER
    ).compile()
    EXAMPLES = ["41 / 3", "32 / 4"]

    @classmethod
    def validate(cls, groupdict: DateDict) -> Optional[DateDict]:
        if int(groupdict["year"]) != 0:
            return groupdict
        return None


class MonthNumberDay(NumberSepNumber):
    """Match a date with the format '6/1', '6 - 1'."""

    PATTERN = NumberSepNumber.TEMPLATE.format(
        first=NAMED_MONTH_NUMBER, second=NAMED_DAY
    ).compile()
    EXAMPLES = ["6/1", "6 - 1"]


class DayMonthNumber(NumberSepNumber):
    """Match a date with the format '13/5', '13 - 5'."""

    PATTERN = NumberSepNumber.TEMPLATE.format(
        first=NAMED_DAY, second=NAMED_MONTH_NUMBER
    ).compile()
    EXAMPLES = ["13/5", "13 - 5"]


class YearMonthNumberDay(DateAlike):
    """Match a date with the format '2021/6/1', '2021 - 6 - 1', '21 - 6 - 1'."""

    # Note: The two separators can be different (e.g., "2021/6-1", "2021-6/1")
    PATTERN = (
        (NAMED_YEAR + SEP + NAMED_MONTH_NUMBER + SEP + NAMED_DAY)
        .join_with_tail(ANYSPACE)
        .compile()
    )

    EXAMPLES = ["2021/6/1", "2021 - 6 - 1", "21 - 6 - 1", "21-5/1", "0/1/1"]


class DayMonthNameYear(DateAlike):
    """Match a date with the format '1 June 2021', '1 - Jun - 2021', '1Jun2021'"""

    # Note: The two separators can be different, such as "1-Jun2021"
    PATTERN = (
        (
            NAMED_DAY
            # Separator can be a dash, a space, a slash, or an empty string
            + (SEP | SPACE.maybe())
            + NAMED_MONTH_LETTER
            # Separator can be a dash, a space, a slash, or an empty string
            + (SEP | SPACE.maybe())
            + NAMED_YEAR
        )
        .join_with_tail(ANYSPACE)
        .compile()
    )

    EXAMPLES = ["1 June 2021", "1 - Jun - 2021", "1Jun2021", "1-Jun2021"]


class MonthNameDayYear(DateAlike):
    """Match a date with the format 'June , 1 - 2021', 'Jun - 1 , 2021'."""

    FIRST_SEP_IS_COMMA = (
        NAMED_MONTH_LETTER
        + COMMA
        + SPACE
        + NAMED_DAY
        # The second separator can be a dash, a slash, or comma with space
        + (SEP | COMMA + SPACE)
        + NAMED_YEAR
    ).join_with_tail(ANYSPACE)

    SECOND_SEP_IS_COMMA = (
        (
            NAMED_MONTH_LETTER
            # Separator can be a dash, a space, a slash, or an empty string
            + (SEP | SPACE.maybe())
            + NAMED_DAY
            + COMMA
            + SPACE  # Space is required after comma
            + NAMED_YEAR
        )
        .join_with_tail(ANYSPACE)
        .clone()
    )

    PATTERN = (FIRST_SEP_IS_COMMA | SECOND_SEP_IS_COMMA).compile()

    EXAMPLES = [
        "June1, 2021",
        "June 1, 2021",
        "Jun - 1 , 2021",
        "Jun / 1 , 2021",
        "June , 1 - 2021",
        "June , 1 , 2021",
        "June , 1 / 2021",
    ]


class LetterSepNumber(DateAlike):

    TEMPLATE = (
        Placeholder("first") + (SEP | SPACE.maybe()) + Placeholder("second")
    ).join_with_tail(ANYSPACE)


class MonthNameYear(LetterSepNumber):
    """Match a date with the format 'June 2021', 'Jun - 2021', 'Jun / 2021', 'Jun2021', 'Jun0', 'Jun99'"""

    PATTERN = LetterSepNumber.TEMPLATE.format(
        first=NAMED_MONTH_LETTER, second=NAMED_YEAR
    ).compile()

    EXAMPLES = [
        "June 2021",
        "Jun - 2021",
        "Jun / 2021",
        "Jun2021",
        "Jun0",
        "Jun99",
    ]


class MonthNameDay(LetterSepNumber):
    """Match a date with the format 'June 1', 'Jun - 1', 'Jun / 1', 'Jun1'"""

    PATTERN = LetterSepNumber.TEMPLATE.format(
        first=NAMED_MONTH_LETTER, second=NAMED_DAY
    ).compile()

    EXAMPLES = [
        "June 1",
        "Jun - 1",
        "Jun / 1",
        "Jun1",
    ]


class DateFeatureDateTimeOnly(DateAlike): ...


class MonthNumberDayYearDateTimeOnly(DateFeatureDateTimeOnly):
    EXAMPLES = ["2 , 11-2021", "11, 2/2021"]
    PATTERN = (
        (
            NAMED_MONTH_NUMBER
            + (COMMA + SOMESPACE).group()
            + NAMED_DAY
            + (SEP | SOMESPACE | (COMMA + SOMESPACE).group())
            + NAMED_YEAR
        ).join_with_tail(ANYSPACE)
        | (
            NAMED_MONTH_NUMBER
            + (SEP | SOMESPACE | (COMMA + SOMESPACE).group())
            + NAMED_DAY
            + (COMMA + SOMESPACE).group()
            + NAMED_YEAR
        )
        .clone()
        .join_with_tail(ANYSPACE)
    ).compile()
