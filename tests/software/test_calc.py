import pytest
from pathlib import Path
from wizard.software.calc import Calc


@pytest.fixture(scope="function")
def dummy_calc():
    wkdir = Path("/tmp")
    return Calc(wkdir, "host", "port")


def test_evaluate_text(dummy_calc: Calc):
    def evaluate(b, t):
        return b

    dummy_calc.evaluate = evaluate

    assert dummy_calc.evaluate_text("1") == "1"
    assert dummy_calc.evaluate_text("1.0") == "1.0"
    assert dummy_calc.evaluate_text("1.0") == "1.0"

    assert dummy_calc.evaluate_texts(["1", "1.0", "1.0"]) == ["1", "1.0", "1.0"]
