import pytest
import re
from typing import Optional
from datetime import datetime
from pathlib import Path
from wizard.app.common.rule.decisions import (
    DecisionTree,
    BranchNodeBuilder,
    LeafNodeBuilder,
    Type,
)
from wizard.feature import Feature


class IsTooLong(Feature):
    TYPE = "Text"

    @classmethod
    def evaluate(cls, s: str) -> tuple[bool, str]:
        return len(s) > 308, s


class DigitHyphenDigit(Feature):
    TYPE = "Text"

    @classmethod
    def evaluate(cls, s: str) -> tuple[bool, str]:
        if cls.tokenization(s):
            return True
        else:
            return False

    @classmethod
    def tokenization(cls, input: str) -> Optional[dict[str, str]]:
        pattern = re.compile(r"^(?P<d1>\d+)-(?P<d2>\d+)$")
        if match := pattern.match(input):
            return match.groupdict()
        else:
            return None


class MonthDay(Feature):
    TYPE = "Datetime"

    @classmethod
    def evaluate(cls, s: str) -> bool:
        if tokens := cls.tokenization(s):
            month = cls.month_mapper(tokens["month"])
            day = cls.day_mapper(tokens["day"])
            if month is not None and day is not None:
                return cls.aggregation(month, day) is not None
            else:
                return False
        else:
            return False

    @classmethod
    def tokenization(cls, input: str) -> Optional[dict[str, str]]:
        pattern = re.compile(r"^(?P<month>\d+)-(?P<day>\d+)$")
        if match := pattern.match(input):
            return match.groupdict()
        else:
            return None

    @classmethod
    def month_mapper(cls, month: str) -> Optional[int]:
        if 1 <= int(month) <= 12:
            return int(month)
        else:
            return None

    @classmethod
    def day_mapper(cls, day: str) -> Optional[int]:
        if 1 <= int(day) <= 31:
            return int(day)
        else:
            return None

    @classmethod
    def aggregation(cls, month: int, day: int) -> Optional[datetime]:
        try:
            return datetime(year=2025, month=month, day=day)
        except ValueError:
            return None


class MonthYear(Feature):
    TYPE = "Datetime"

    @classmethod
    def evaluate(cls, s: str) -> bool:
        if tokens := cls.tokenization(s):
            month = cls.month_mapper(tokens["month"])
            year = cls.year_mapper(tokens["year"])
            if month is not None and year is not None:
                return cls.aggregation(month, year) is not None
            else:
                return False

    @classmethod
    def tokenization(cls, input: str) -> Optional[dict[str, str]]:
        pattern = re.compile(r"^(?P<month>\d+)-(?P<year>\d+)$")
        if match := pattern.match(input):
            return match.groupdict()
        else:
            return None

    @classmethod
    def month_mapper(cls, month: str) -> Optional[int]:
        if 1 <= int(month) <= 12:
            return int(month)
        else:
            return None

    @classmethod
    def year_mapper(cls, year: str) -> Optional[int]:
        if 1 <= int(year) <= 9999:
            return int(year)
        else:
            return None

    @classmethod
    def aggregation(cls, month: int, year: int) -> Optional[datetime]:
        try:
            return datetime(year=year, month=month, day=1)
        except ValueError:
            return None


@pytest.fixture
def tree() -> DecisionTree:
    text_parser = lambda s: s
    maybe_date = (
        BranchNodeBuilder()
        .feature(DigitHyphenDigit)
        .on_true(
            BranchNodeBuilder()
            .feature(MonthDay)
            .on_true(
                LeafNodeBuilder()
                .typ(Type.DATETIME)
                .scalar_value_parser(text_parser)
                .cell_value_parser(text_parser)
                .build()
            )
            .build()
        )
        .on_false(
            BranchNodeBuilder()
            .feature(MonthYear)
            .on_true(
                LeafNodeBuilder()
                .typ(Type.DATETIME)
                .scalar_value_parser(text_parser)
                .cell_value_parser(text_parser)
                .build()
            )
            .build()
        )
        .build()
    )

    root = BranchNodeBuilder().feature(IsTooLong).on_false(maybe_date).build()

    return DecisionTree(root)


@pytest.mark.parametrize("input", ["12-1"])
def test_month_day(tree: DecisionTree, input: str):
    tree.decide(input)
    trace = tree.get_trace(input)
    tree.to_svg(path=Path("decision_tree_month_day.svg"), trace=trace, full=False)


@pytest.mark.parametrize("input", ["12-32", "1-2025"])
def test_month_year(tree: DecisionTree, input: str):
    tree.decide(input)
    trace = tree.get_trace(input)
    tree.to_svg(path=Path("decision_tree_month_year.svg"), trace=trace, full=False)


@pytest.mark.parametrize("input", ["1" * 309, "123"])
def test_text(tree: DecisionTree, input: str):
    tree.decide(input)
    trace = tree.get_trace(input)
    tree.to_svg(path=Path("decision_tree_text.svg"), trace=trace, full=True)
