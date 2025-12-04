from typing import Optional

from wizard.features.common.datetime_alike.datetime import DatetimeDict
from wizard.feature import WeirdFeature

from .utils import DateTimeUtils
from .base import CalcDateTimeAlikeBase, DateDict
from ...common.pattern import Primitive, Placeholder
from wizard.typ import GregorianDateTime

DOT = Primitive.dot()
DASH = Primitive.hyphen()
SLASH = Primitive.slash()
COMMA = Primitive.comma()

NAMED_YEAR = Primitive.digits().named("year")
NAMED_MONTH_NUMBER = Primitive.digits().named("month")
NAMED_DAY = Primitive.digits().named("day")

NAMED_MONTH_LETTER = Primitive.letters().named("month")
NAMED_MONTH_LETTER_DOT = (Primitive.letters() + DOT).named("month").group()

MONTH = (NAMED_MONTH_LETTER | NAMED_MONTH_LETTER_DOT).group().clone()
NAMED_DAY_OF_WEEK_SEP = (
    (Primitive.letters() + Primitive.comma().maybe() + Primitive.somespace())
    # the name day_of_week is intentional
    .named("day_of_week")
    .maybe()
    .group()
)

ANYSPACE = Primitive.anyspace()
SOMESPACE = Primitive.somespace()


utils = DateTimeUtils()

WITH_DAY_OF_WEEK = (NAMED_DAY_OF_WEEK_SEP + Placeholder("date")).group()


class DateAlike(CalcDateTimeAlikeBase):
    TYPE = "Datetime"

    @classmethod
    def is_datetime_valid(
        cls,
        **kwargs: DateDict,
    ) -> Optional[GregorianDateTime]:
        day_of_week, year, month, day = (
            kwargs.get("day_of_week", None),
            kwargs.get("year", GregorianDateTime.today().year),
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
            return GregorianDateTime(year, month, day)
        except ValueError:
            return None


# These patterns are built-in default patterns that are not configurable.
class BuiltinPattern(DateAlike):
    pass


# These patterns are configurable patterns that can be customized by users.
class ConfigurablePattern(DateAlike):
    pass


class YearMonthNumberDayExpected(BuiltinPattern):
    EXAMPLES = [
        "2021-1-1",
        " 0-1-1",
        "13-1-3",
        "12-1-1",
        "1-1-1",
        "Mon 2021-1-1",
        "Monday, 0-1-1",
    ]
    COUNTER_EXAMPLES = ["Mon, 0-1-1"]

    # The separator can only be a dash.
    PATTERN = WITH_DAY_OF_WEEK.format(
        date=(
            NAMED_YEAR + DASH + NAMED_MONTH_NUMBER + DASH + NAMED_DAY
        ).surround_anyspace()
    ).compile()


class YearMonthNumberDayBuggy(YearMonthNumberDayExpected):
    EXAMPLES = ["2021-1-1", " 0-1-1", "13-1-3", "0012-1-1"]

    @classmethod
    def validate(cls, groupdict: DatetimeDict) -> Optional[DateDict]:
        """Validate that the rule (YMD) is not ambiguous with other rules (DMY, MDY).

        When the year has exactly one/two digits and is between 01-12, it could be ambiguous with month numbers
        depending on the locale's date format (MDY vs DMY). For example, in '12-1-1':
        - In MDY locales: 12 could be interpreted as December
        - In DMY locales: 12 could be interpreted as the day

        More details: https://bugs.documentfoundation.org/show_bug.cgi?id=164239
        """
        # Note: no typo here - if the year value could be a valid month number (1-12),
        # we intentionally reject it to avoid ambiguity with month-first formats
        if utils.get_month(groupdict["year"]) is not None:
            return None
        return groupdict


class NumberMonthNameNumber(BuiltinPattern):
    # The separator can only be a dash.
    TEMPLATE = (
        Placeholder("first") + DASH + NAMED_MONTH_LETTER + DASH + Placeholder("second")
    ).surround_anyspace()


# DayMonthNameYear has higher priority than YearMonthNameDay.
class DayMonthNameYear(NumberMonthNameNumber):
    EXAMPLES = ["1-Jan-2021", "1-Jan-0", "Wednesday, 1-Jan-2021"]
    PATTERN = WITH_DAY_OF_WEEK.format(
        date=NumberMonthNameNumber.TEMPLATE.format(first=NAMED_DAY, second=NAMED_YEAR)
    ).compile()


class YearMonthNameDay(NumberMonthNameNumber):
    EXAMPLES = ["0-Jan-1", "2024-march-20", "Tue 0-Jan-1"]
    PATTERN = WITH_DAY_OF_WEEK.format(
        date=NumberMonthNameNumber.TEMPLATE.format(first=NAMED_YEAR, second=NAMED_DAY)
    ).compile()


class MonthNameNumber(BuiltinPattern):
    # The dot can be treated either as part of the month name or as a separator:
    # - When treated as part of month name: separator can be dash, slash, or space(s)
    # - When treated as separator: dot itself acts as the separator

    ORDINARY_SEP = (ANYSPACE + (SLASH | DASH)).group()
    TEMPLATE = (
        # The MonthName can be followed by any space, but the separator cannot be followed by space
        (
            (NAMED_MONTH_LETTER_DOT + (ANYSPACE | ORDINARY_SEP).group())
            | (NAMED_MONTH_LETTER + (SOMESPACE | ORDINARY_SEP).group())
        ).group()
        + Placeholder("first")
        # Optional trailing slash or dot is allowed in LibreOffice Calc date formats
        + (
            (ANYSPACE + SLASH).group()
            | (DOT + (ANYSPACE + SLASH).maybe().group()).group()
        ).maybe()
    ).surround_anyspace()


# MonthNameDay has higher priority than MonthNameYear.
class MonthNameDay(MonthNameNumber):
    EXAMPLES = [
        "Jun.01",
        "Jun.-20",
        "Jan  22",
        "Mar. /22",
        "Mar. /22/",
        "Mar.01 /",
        "Wednesday Jun.-21",
    ]
    PATTERN = WITH_DAY_OF_WEEK.format(
        date=MonthNameNumber.TEMPLATE.format(first=NAMED_DAY).clone()
    ).compile()

    @classmethod
    def validate(cls, groupdict: DateDict) -> Optional[DateDict]:
        """Validate that the month and day are valid.

        When a number follows a month name, it could be interpreted as either a day, text, or a year.
        - If the month and day is valid date, the number is treated as a day (handled by this class)

        More details: https://bugs.documentfoundation.org/show_bug.cgi?id=164357
        """
        if (month := utils.get_month(groupdict["month"])) is not None and (
            day := utils.get_day(groupdict["day"])
        ) is not None:
            # if month and day are valid, return the groupdict
            try:
                GregorianDateTime(month=month, day=day)
                return groupdict
            except Exception:
                return None
        return None


class MonthNameYear(MonthNameNumber):
    EXAMPLES = [
        "Jun.32",
        "Jun.-33",
        "Jan  33",
        "Mar. /00",
        "Jan -77",
        "Mar. /00/",
        "Mar.33 /",
        "Feb-33/",
        "Feb-33.",
        "Jun-001",
        "Thursday, Jun.32",
    ]
    PATTERN = WITH_DAY_OF_WEEK.format(
        date=MonthNameNumber.TEMPLATE.format(first=NAMED_YEAR).clone()
    ).compile()

    @classmethod
    def validate(cls, groupdict: DatetimeDict) -> Optional[DateDict]:
        """Validate that the input should be treated as a year rather than a day.

        When a number follows a month name, it could be interpreted as either a day, text, or a year.
        LibreOffice Calc uses the following rules to disambiguate:
        - If the number is > 31, it is treated as a year (handled by this class)

        More details: https://bugs.documentfoundation.org/show_bug.cgi?id=164357
        """
        digit_year = groupdict["year"]
        if len(digit_year) == 2 and 1 <= int(digit_year) <= 31:
            return None

        return groupdict


class MonthNumberDay(ConfigurablePattern):
    EXAMPLES = ["12/1", "12/01", "Sunday, 12/1", "Friday 12/5"]
    # The separator must be a slash.
    PATTERN = WITH_DAY_OF_WEEK.format(
        date=(NAMED_MONTH_NUMBER + SLASH + NAMED_DAY).surround_anyspace()
    ).compile()


class MonthNumberDayYear(ConfigurablePattern):
    EXAMPLES = ["12/1/1", "12/1/2021", "12/01/32767", "Sunday, 12/1/1"]

    # The separator can only be a slash.
    PATTERN = WITH_DAY_OF_WEEK.format(
        date=(
            NAMED_MONTH_NUMBER + SLASH + NAMED_DAY + SLASH + NAMED_YEAR
        ).surround_anyspace()
    ).compile()


class DateFeatureDateTimeOnly(BuiltinPattern): ...


class MonthNumberDayYearDateTimeOnly(DateFeatureDateTimeOnly):
    EXAMPLES = ["12-1-1", "12-1-1", "12-01-030"]

    PATTERN = WITH_DAY_OF_WEEK.format(
        date=(
            NAMED_MONTH_NUMBER + DASH + NAMED_DAY + DASH + NAMED_YEAR
        ).surround_anyspace()
    ).compile()

    @classmethod
    def validate(cls, groupdict: DateDict) -> Optional[DateDict]:
        # weird enough aha?
        if 1 <= int(groupdict["year"]) <= 31:
            return groupdict
        return None


class MonthNumberDayYear2DateTimeOnly(DateFeatureDateTimeOnly):
    EXAMPLES = ["12/1 1", "12/1 100"]

    PATTERN = WITH_DAY_OF_WEEK.format(
        date=(
            NAMED_MONTH_NUMBER + SLASH + NAMED_DAY + SOMESPACE + NAMED_YEAR
        ).surround_anyspace()
    ).compile()


class MonthNumberDayDateTimeOnly(DateFeatureDateTimeOnly):
    EXAMPLES = ["1-12", "1-1", "Sunday, 1-12"]

    PATTERN = WITH_DAY_OF_WEEK.format(
        date=(ANYSPACE + NAMED_MONTH_NUMBER + DASH + NAMED_DAY)
    ).compile()

    @classmethod
    def validate(cls, groupdict: DateDict) -> Optional[DateDict]:
        # weird enough aha?
        if 1 <= int(groupdict["day"]) <= 12:
            return groupdict
        return None


class YearMonthNumberDateTimeOnly(DateFeatureDateTimeOnly):
    EXAMPLES = ["0-1", "32767-12"]
    PATTERN = WITH_DAY_OF_WEEK.format(
        date=(ANYSPACE + NAMED_YEAR + DASH + NAMED_MONTH_NUMBER)
    ).compile()

    @classmethod
    def validate(cls, groupdict: DateDict) -> Optional[DateDict]:
        # weird enough aha?
        # Year should be a valid year and must not conflict with or be interpretable as a month number.
        if (
            utils.get_year(groupdict["year"])
            and utils.get_month(groupdict["year"]) is None
            and utils.get_month(groupdict["month"])
        ):
            return groupdict
        return None


class MonthNameDayYear(BuiltinPattern):
    EXAMPLES = [
        "Jun. 01, 2021",
        "Jun.-20, 2021",
        "Jan  22, 2021",
        "Mar. /22 , 2021",
        "Mar. /22/ , 2021",
        "Mar. /22/ , 2021/",
        "Feb.-01 / , 2021",
        "Mar22 /, 2021 /",
        "Jun. 01./, 2021",
        "Sat Jun.-20, 2021",
    ]

    # The dot can be treated either as part of the month name or as a separator - both cases are unified here.
    # Between month and day, valid separators are: dash, slash, or any number of spaces.
    # After the day, a comma and at least one space must precede the year.
    NAMED_DOT = DOT.named("additional_dot")
    MONTH_NAME_DAY_YEAR_TEMPLATE = (
        (
            MONTH
            + ANYSPACE
            + (SLASH | DASH | ANYSPACE).group()
            + NAMED_DAY
            # Optional anyspace + slash and dot after the day is allowed in LibreOffice Calc date formats
            + (
                ((ANYSPACE + SLASH).maybe().group() + ANYSPACE)
                | NAMED_DOT
                | (NAMED_DOT + SLASH + ANYSPACE).group().clone()
            )
            + COMMA
            + SOMESPACE
            + NAMED_YEAR
            # Optional trailing slash or dot is allowed in LibreOffice Calc date formats
            # A trailing slash must be preceded by anyspace, while a trailing dot do not
            + Placeholder("trailing_slash_or_dot")
        )
        .surround_anyspace()
        .group()
    )

    PATTERN = WITH_DAY_OF_WEEK.format(
        date=MONTH_NAME_DAY_YEAR_TEMPLATE.format(
            trailing_slash_or_dot=(ANYSPACE + SLASH).maybe()
        )
    ).compile()

    @classmethod
    def match(cls, s: str) -> Optional[DatetimeDict]:
        # This method is used by DateTime, so it is a most convinent way to add logic for DateTime.
        # For DateTime, the additional_dot should not exist.
        groupdict, index = super().match(s)
        if groupdict and groupdict.get("additional_dot"):
            return None, 0
        return groupdict, index


class MonthNameDayYear2(BuiltinPattern):
    EXAMPLES = [
        "Mar.3/2021",
        "Mar. 3/2021",
        "Mar /1 /2021",
        "Mar 5 2024",
        "Mar/1/2021",
        "Mar /1/2021",
        "Jun1 2021",
        "Jun. 1 2021",
        "Jun-1 2021",
        "Jun-1 2021/",
        "Jun. 01/ 2021",
        "Thu Mar.3/2021",
    ]
    NAMED_DOT = DOT.named("additional_dot")
    SECOND_SEPARATOR_IS_SLASH_OR_SPACE_TEMPLATE = (
        (
            # The first separator can be empty (no separator), a slash, a dash, or some spaces.
            # The second separator can be a slash or some spaces.
            # Between month and first separator: optional spaces and/or slash.
            # Separators tightly bind to the succeeding parts (day and year).
            MONTH
            + ((SLASH.maybe() | DASH | SOMESPACE) + NAMED_DAY).group()
            + ((SLASH + ANYSPACE | SOMESPACE) + NAMED_YEAR).group()
        )
        # Optional trailing slash or dot is allowed in LibreOffice Calc date formats
        .join_with_head(ANYSPACE)
        + Placeholder("trailing_slash_or_dot")
    ).group()

    PATTERN = WITH_DAY_OF_WEEK.format(
        date=(
            (
                SECOND_SEPARATOR_IS_SLASH_OR_SPACE_TEMPLATE.format(
                    trailing_slash_or_dot=SLASH.maybe()
                )
            )
            | (
                # The separator, day, dot, and year must be tightly bound together without any spaces between them
                MONTH
                + (
                    ((ANYSPACE + (SLASH.maybe() | DASH)) | SOMESPACE)
                    + NAMED_DAY
                    + (NAMED_DOT | (NAMED_DOT + SLASH + ANYSPACE).group())
                    + NAMED_YEAR
                )
                + SLASH.maybe()
            )
            .clone()
            .surround_anyspace()
        )
    ).compile()

    @classmethod
    def match(cls, s: str) -> Optional[DatetimeDict]:
        groupdict, index = super().match(s)
        if groupdict and groupdict.get("additional_dot"):
            return None, 0
        return groupdict, index


class MonthNameDayYearEndWithDotSlash(BuiltinPattern):
    EXAMPLES = [
        "Mar. /22/ , 2021.",
        "Jun-1 2021.",
        "Mar22 /, 2021.",
        "Friday, Mar. /22/ , 2021.",
        "Sun Jun-1 2021.",
    ]

    PATTERN = WITH_DAY_OF_WEEK.format(
        date=(
            MonthNameDayYear.MONTH_NAME_DAY_YEAR_TEMPLATE.format(
                trailing_slash_or_dot=(DOT + (ANYSPACE + SLASH).maybe().group()).maybe()
            )
            | MonthNameDayYear2.SECOND_SEPARATOR_IS_SLASH_OR_SPACE_TEMPLATE.format(
                trailing_slash_or_dot=(DOT + (ANYSPACE + SLASH).maybe().group()).maybe()
            )
        ).clone()
    ).compile()


class ChaoticDate(WeirdFeature, DateAlike):
    EXAMPLES = ["Mar3:2021", "Mar/3:2021", "Mar.3 : 2021", "Mar /3 : 2021"]

    PATTERN = (
        (
            NAMED_MONTH_LETTER
            + (
                ((ANYSPACE + SLASH).maybe().group() + ANYSPACE)
                | (DOT + ANYSPACE).group()
                | (DOT + SLASH + ANYSPACE).group()
            )
            + NAMED_DAY
            + ANYSPACE
            + Primitive.colon()
            + ANYSPACE
            + NAMED_YEAR
        )
        .surround_anyspace()
        .compile()
    )

    @classmethod
    def evaluate(cls, s: str) -> bool:
        match, _ = cls.match(s)
        if match:
            return True
        return False
