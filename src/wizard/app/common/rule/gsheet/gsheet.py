from typing import Self

from wizard.features.common.text import LeadingApostrophe

from ..decisions import DecisionTree, BranchNodeBuilder, BranchNode
from .router import *
from wizard.features.gsheet import *
from wizard.feature import load_weird_features, load_discard_features


class GsheetTypeCasting(DecisionTree):
    @classmethod
    def build_tree(cls) -> Self:
        return cls(
            cls._general(),
            load_weird_features("gsheet").values(),
            load_discard_features("gsheet").values(),
        )

    @staticmethod
    def _general() -> BranchNode:

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
                        GsheetTypeCasting._datetime_builder(),
                        GsheetTypeCasting._symbolic_number_builder(),
                        GsheetTypeCasting._one_digits_group_builder(),
                        GsheetTypeCasting._two_digits_groups_builder(),
                        GsheetTypeCasting._three_digits_groups_builder(),
                        GsheetTypeCasting._four_digits_groups_builder(),
                    )
                )
                .build()
            )
            .build()
        )

    @staticmethod
    def _one_digits_group_builder() -> BranchNodeBuilder:
        return (
            BranchNodeBuilder()
            .feature(HasOneDigitsGroup)
            .on_true(
                BranchNodeBuilder()
                .feature(HasMonthName)
                .on_true(
                    BranchNodeBuilder()
                    .feature(LettersDigitsRouter)
                    .branch(
                        LettersDigitsRouterType.MD,
                        BranchNodeBuilder().feature(MonthNameDay).build(),
                    )
                    .branch(
                        LettersDigitsRouterType.MY,
                        BranchNodeBuilder().feature(MonthNameYear).build(),
                    )
                    .branch(
                        LettersDigitsRouterType.NEXT,
                        BranchNodeBuilder()
                        .feature(DigitsLettersRouter)
                        .branch(
                            DigitsLettersRouterType.DM,
                            BranchNodeBuilder().feature(DayMonthName).build(),
                        )
                        .branch(
                            DigitsLettersRouterType.YM,
                            BranchNodeBuilder().feature(YearMonthNumber).build(),
                        )
                        .build(),
                    )
                    .build()
                )
                .build()
            )
            .on_false(BranchNodeBuilder().feature(Hour).build())
        )

    @staticmethod
    def _two_digits_groups_builder() -> BranchNodeBuilder:
        return (
            BranchNodeBuilder()
            .feature(HasTwoDigitsGroups)
            .on_true(
                BranchNodeBuilder()
                .feature(HasMonthName)
                .on_true(
                    BranchNodeBuilder.build_false_chain(
                        DayMonthNameYear,
                        YearMonthNameDay,
                        MonthNameDayYear,
                    )
                )
                .on_false(
                    BranchNodeBuilder()
                    .feature(MaybeTime)
                    .on_true(BranchNodeBuilder().feature(HourMinute).build())
                    .on_false(
                        BranchNodeBuilder()
                        .feature(DoubleDigitsRouter)
                        .branch(
                            DoubleDigitsRouterType.MD,
                            BranchNodeBuilder().feature(MonthNumberDay).build(),
                        )
                        .branch(
                            DoubleDigitsRouterType.MY,
                            BranchNodeBuilder().feature(MonthNumberYear).build(),
                        )
                        .branch(
                            DoubleDigitsRouterType.YM,
                            BranchNodeBuilder().feature(YearMonthNumber).build(),
                        )
                        .build(),
                    )
                    .build()
                )
                .build()
            )
        )

    @staticmethod
    def _three_digits_groups_builder() -> BranchNodeBuilder:
        return (
            BranchNodeBuilder()
            .feature(HasThreeDigitsGroups)
            .on_true(
                BranchNodeBuilder.build_false_chain(
                    MonthNumberDayYear, YearMonthNumberDay, HourMinuteSecond
                )
            )
        )

    @staticmethod
    def _four_digits_groups_builder() -> BranchNodeBuilder:
        return (
            BranchNodeBuilder()
            .feature(HasFourDigitsGroups)
            .on_true(BranchNodeBuilder().feature(HourMinuteSecondMicrosecond).build())
        )

    @staticmethod
    def _symbolic_number_builder() -> BranchNodeBuilder:
        """Build branch nodes for numeric formats: currency, percentages, fractions, etc."""
        return (
            BranchNodeBuilder()
            .feature(MaybeSymbolicNumber)
            .on_true(
                BranchNodeBuilder()
                .feature(SymbolicNumberRouter)
                .branch(
                    SymbolicNumberRouterType.SCIENTIFIC,
                    BranchNodeBuilder.build_false_chain(IsIntegerE, IsFloatE),
                )
                .branch(
                    SymbolicNumberRouterType.CURRENCY,
                    BranchNodeBuilder().feature(IsCurrency).build(),
                )
                .branch(
                    SymbolicNumberRouterType.PERCENTAGE,
                    BranchNodeBuilder().feature(IsPercent).build(),
                )
                .build()
            )
        )

    @staticmethod
    def _datetime_builder() -> BranchNodeBuilder:
        return (
            BranchNodeBuilder()
            .feature(MaybeDateTime)
            .on_true(BranchNodeBuilder().feature(DateTimeAlike).build())
        )
