import pytest

from wizard.app.common.rule.calc import CalcTypeCasting
from wizard.typ import Text, Bool, Int, Float, GregorianDateTime


class TestCalcTypeCasting:
    @pytest.fixture
    def calc(self) -> CalcTypeCasting:
        return CalcTypeCasting.build_tree()

    @pytest.mark.parametrize(
        "input, expected_type",
        [
            ("12:00", GregorianDateTime),
            ("1.", Float),
            ("1", Int),
            ("hello world", Text),
            ("true", Bool),
        ],
    )
    def test_output_type(self, calc: CalcTypeCasting, input: str, expected_type: type):
        assert isinstance(calc.decide(input), expected_type)
