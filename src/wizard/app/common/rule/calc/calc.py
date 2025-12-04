from typing import Self

from ..decisions import (
    DecisionTree,
    BranchNodeBuilder,
    BranchNode,
)
from .router import *
from wizard.features.calc import *
from wizard.feature import load_weird_features, load_discard_features
from wizard.features.common.text import LeadingApostrophe


class CalcTypeCasting(DecisionTree):

    @classmethod
    def build_tree(cls) -> Self:
        return cls(
            cls._general(),
            load_weird_features("calc").values(),
            load_discard_features("calc").values(),
        )

    @staticmethod
    def _general() -> BranchNode:
        """Build a branch node for all strings."""
        return (
            BranchNodeBuilder()
            .feature(LeadingApostrophe)
            .on_false(
                BranchNodeBuilder()
                .feature(HasDigits)
                .on_false(BranchNodeBuilder().feature(Boolean).build())
                .on_true(
                    BranchNodeBuilder.build_false_chain(
                        IsTooLong,
                        IsInteger,
                        IsFloat,
                        CalcTypeCasting._datetime_builder(),
                        CalcTypeCasting._symbolic_number_builder(),
                        CalcTypeCasting._one_digits_group_builder(),
                        CalcTypeCasting._two_digits_groups_builder(),
                        CalcTypeCasting._three_digits_groups_builder(),
                        CalcTypeCasting._four_digits_groups_builder(),
                    )
                )
                .build()
            )
            .build()
        )

    @staticmethod
    def _datetime_builder() -> BranchNodeBuilder:
        """Build a branch node for datetime strings."""
        return (
            BranchNodeBuilder()
            .feature(MaybeDateTime)
            .on_true(
                BranchNodeBuilder()
                .feature(MaybeISO8601DateTime)
                .branch(
                    MaybeISO8601DateTimeType.ISO8601.value,
                    BranchNodeBuilder.build_false_chain(
                        ISO8601DateTime,
                        ISO8601DateTimeWithApm,
                    ),
                )
                .branch(
                    MaybeISO8601DateTimeType.NEXT.value,
                    BranchNodeBuilder.build_false_chain(
                        DateTimeWithNumericMonth,
                        DateTimeWithNamedMonth,
                        PartialDateWithTime,
                    ),
                )
                .build()
            )
        )

    @staticmethod
    def _symbolic_number_builder() -> BranchNodeBuilder:
        """Build branch nodes for numeric formats: currency, percentages, fractions, etc."""
        # fmt: off
        return (
            BranchNodeBuilder()
            .feature(MaybeSymbolicNumber)
            .on_true(
                BranchNodeBuilder()
                .feature(SymbolicNumberRouterFeature)
                .branch(SymbolicNumberRouterType.CURRENCY.value, BranchNodeBuilder().feature(IsCurrency).build())
                .branch(SymbolicNumberRouterType.PERCENTAGE.value, BranchNodeBuilder().feature(IsPercent).build())
                .branch(SymbolicNumberRouterType.SCIENTIFIC.value, BranchNodeBuilder.build_false_chain(IsIntegerE, IsFloatE))
                .build()
            )
        )
        # fmt: on

    @staticmethod
    def _one_digits_group_builder() -> BranchNodeBuilder:
        """Build a branch node for those strings that only have one consecutive digits group."""
        # fmt: off
        return (
            BranchNodeBuilder()
            .feature(HasOneDigitsGroup)
            .on_true(
                BranchNodeBuilder()
                .feature(HasMonthName)
                .on_true(
                    BranchNodeBuilder()
                    .feature(LettersDigitsRouterFeature)
                    .branch(LettersDigitsRouterType.MD.value, BranchNodeBuilder().feature(MonthNameDay).build())
                    .branch(LettersDigitsRouterType.MY.value, BranchNodeBuilder().feature(MonthNameYear).build())
                    .build()
                )
                .on_false(
                    BranchNodeBuilder()
                    .feature(Hour)
                    .on_false(
                        BranchNodeBuilder()
                        .feature(HourSpecial)
                        .build()
                    )
                    .build()
                ).build()
            )
        )
        # fmt: on

    @staticmethod
    def _two_digits_groups_builder() -> BranchNodeBuilder:
        """Build a branch node for those strings that have two consecutive digits groups."""

        def has_month_name() -> BranchNode:
            return (
                BranchNodeBuilder()
                .feature(DigitsLettersDigitsRouterFeature)
                .branch(
                    DigitsLettersDigitsRouterType.DMY.value,
                    BranchNodeBuilder().feature(DayMonthNameYear).build(),
                )
                .branch(
                    DigitsLettersDigitsRouterType.YMD.value,
                    BranchNodeBuilder().feature(YearMonthNameDay).build(),
                )
                .branch(
                    DigitsLettersDigitsRouterType.NEXT.value,
                    BranchNodeBuilder.build_false_chain(
                        MonthNameDayYear,
                        MonthNameDayYear2,
                        MonthNameDayYearEndWithDotSlash,
                    ),
                )
                .build()
            )

        def maybe_time() -> BranchNode:
            return BranchNodeBuilder.build_false_chain(
                HourMinute,
                HourMinuteSpecial,
                HMDot,
            )

        return (
            BranchNodeBuilder()
            .feature(HasTwoDigitsGroups)
            .on_true(
                BranchNodeBuilder()
                .feature(HasMonthName)
                .on_true(has_month_name())
                .on_false(
                    BranchNodeBuilder()
                    .feature(MaybeTime)
                    .on_true(maybe_time())
                    .on_false(BranchNodeBuilder().feature(MonthNumberDay).build())
                    .build()
                )
                .build()
            )
        )

    @staticmethod
    def _three_digits_groups_builder() -> BranchNodeBuilder:
        """Build a branch node for those strings that have three consecutive digits groups."""

        def maybe_time() -> BranchNode:
            return (
                BranchNodeBuilder()
                .feature(HMSorMSM)
                .branch(
                    HMSorMSMType.HMS.value,
                    BranchNodeBuilder.build_false_chain(
                        HourMinuteSecond,
                        HourMinuteSecondSpecial,
                        HMSDot,
                        HMSWithSpaceAsFirstSep,
                        HMSWithSpaceAsFirstSepWithAdditionalSuffix,
                    ),
                )
                .branch(
                    HMSorMSMType.MSM.value,
                    BranchNodeBuilder.build_false_chain(
                        MinuteSecondMicrosecond,
                        MinuteSecondMicrosecondNegative,
                        MSMWithSpaceAsFirstSep,
                    ),
                )
                .build()
            )

        return (
            BranchNodeBuilder()
            .feature(HasThreeDigitsGroups)
            .on_true(
                BranchNodeBuilder()
                .feature(MaybeTime)
                .on_true(maybe_time())
                .on_false(
                    BranchNodeBuilder.build_false_chain(
                        IsFraction, YearMonthNumberDayBuggy, MonthNumberDayYear
                    )
                )
                .build()
            )
        )

    @staticmethod
    def _four_digits_groups_builder() -> BranchNodeBuilder:
        """Build a branch node for those strings that have four consecutive digits groups."""
        return (
            BranchNodeBuilder()
            .feature(HasFourDigitsGroups)
            .on_true(
                BranchNodeBuilder.build_false_chain(
                    HourMinuteSecondMicrosecond, HourMinuteSecondMicrosecondNegative
                )
            )
        )
