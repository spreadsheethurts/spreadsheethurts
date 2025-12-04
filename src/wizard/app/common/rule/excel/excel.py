from typing import Self

from ..decisions import DecisionTree, BranchNodeBuilder, BranchNode
from wizard.features.excel import *
from wizard.feature import load_weird_features, load_discard_features
from .router import *


class ExcelTypeCasting(DecisionTree):
    @classmethod
    def build_tree(cls) -> Self:
        return cls(
            cls._general(),
            load_weird_features("excel").values(),
            load_discard_features("excel").values(),
        )

    @staticmethod
    def _general() -> BranchNode:
        return (
            BranchNodeBuilder()
            .feature(ContainsTab)
            .on_false(
                BranchNodeBuilder()
                .feature(HasDigits)
                .on_false(BranchNodeBuilder().feature(Boolean).build())
                .on_true(
                    BranchNodeBuilder.build_false_chain(
                        IsTooLong,
                        IsInteger,
                        IsFloat,
                        IsFraction,
                        ExcelTypeCasting._datetime_builder(),
                        ExcelTypeCasting._symbolic_number_builder(),
                        ExcelTypeCasting._one_digits_group_builder(),
                        ExcelTypeCasting._two_digits_groups_builder(),
                        ExcelTypeCasting._three_digits_groups_builder(),
                        ExcelTypeCasting._four_digits_groups_builder(),
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
                    .feature(LetterDigitsRouter)
                    .branch(
                        LetterDigitsRouterType.MD,
                        BranchNodeBuilder().feature(MonthNameDay).build(),
                    )
                    .branch(
                        LetterDigitsRouterType.MY,
                        BranchNodeBuilder().feature(MonthNameYear).build(),
                    )
                    .branch(
                        LetterDigitsRouterType.NEXT,
                        BranchNodeBuilder().feature(DayMonthName).build(),
                    )
                    .build()
                )
                .on_false(BranchNodeBuilder().feature(Hour).build())
                .build()
            )
        )

    @staticmethod
    def _two_digits_groups_builder() -> BranchNodeBuilder:

        def has_month_name() -> BranchNode:
            return BranchNodeBuilder.build_false_chain(
                DayMonthNameYear, MonthNameDayYear
            )

        def annoying_date() -> BranchNode:
            return (
                BranchNodeBuilder()
                .feature(DoubleDigitsRouter)
                .branch(
                    DoubleDigitsRouterType.MD,
                    BranchNodeBuilder().feature(MonthNumberDay).build(),
                )
                .branch(
                    DoubleDigitsRouterType.DM,
                    BranchNodeBuilder().feature(DayMonthNumber).build(),
                )
                .branch(
                    DoubleDigitsRouterType.YM,
                    BranchNodeBuilder().feature(YearMonthNumber).build(),
                )
                .build()
            )

        def maybe_time() -> BranchNode:
            return BranchNodeBuilder.build_false_chain(HourMinute, HourMinuteSpecial)

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
                    .on_false(annoying_date())
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
                BranchNodeBuilder()
                .feature(MaybeTime)
                .on_true(
                    BranchNodeBuilder()
                    .feature(HMSorMSM)
                    .branch(
                        HMSorMSMType.HMS,
                        BranchNodeBuilder.build_false_chain(
                            HourMinuteSecond, HourMinuteSecondSpecial
                        ),
                    )
                    .branch(
                        HMSorMSMType.MSM,
                        BranchNodeBuilder.build_false_chain(
                            MinuteSecondMicrosecond, MinuteSecondMicrosecondSpecial
                        ),
                    )
                    .build()
                )
                .on_false(BranchNodeBuilder().feature(YearMonthNumberDay).build())
                .build()
            )
        )

    @staticmethod
    def _four_digits_groups_builder() -> BranchNodeBuilder:
        return (
            BranchNodeBuilder()
            .feature(HasFourDigitsGroups)
            .on_true(
                BranchNodeBuilder.build_false_chain(
                    HourMinuteSecondMicrosecond,
                    HourMinuteSecondMicrosecondSpecial,
                )
            )
        )

    @staticmethod
    def _symbolic_number_builder() -> BranchNodeBuilder:

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
                    SymbolicNumberRouterType.PERCENTAGE,
                    BranchNodeBuilder().feature(IsPercent).build(),
                )
                .branch(
                    SymbolicNumberRouterType.CURRENCY,
                    BranchNodeBuilder().feature(IsCurrency).build(),
                )
                .build()
            )
        )

    @staticmethod
    def _datetime_builder() -> BranchNodeBuilder:
        return (
            BranchNodeBuilder()
            .feature(MaybeDateTime)
            .on_true(BranchNodeBuilder.build_false_chain(DateTimeAlike, TimeDateAlike))
        )
