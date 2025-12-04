import pytest
from typing import Dict, List, Tuple, Any

from wizard.app.common.rule.excel import ExcelTypeCasting
from wizard.app.common.rule.gsheet import GsheetTypeCasting
from wizard.app.common.rule.calc import CalcTypeCasting


@pytest.fixture
def large_integer_test_cases() -> Dict[str, List[Tuple[str, Any]]]:
    """Large integer test cases for different spreadsheet software."""
    return {
        "excel": [
            ("00123456789012345000", float(123456789012345000)),
            ("12345678901234567", float(12345678901234500)),
            ("9007199254740991", float(9007199254740990)),
            ("9,007,199,254,740,991", float(9007199254740990)),
        ],
        "gsheet": [
            ("00123456789012345000", 1.23456789012345e+17),
            ("12345678901234567", "12345678901234567"),
            ("9007199254740991", "9007199254740991"),
            ("9,007,199,254,740,991", 9007199254740990.0),
        ],
        "calc": [
            ("00123456789012345000", float(123456789012345000)),
            ("12345678901234567", 1.23456789012346e16),
            ("9007199254740991", 9007199254740991),
            ("9,007,199,254,740,991", 9007199254740991),
        ],
    }


@pytest.fixture
def typecasting_rules() -> Dict[str, Any]:
    """Typecasting rule classes for each software."""
    return {
        "excel": ExcelTypeCasting.build_tree(),
        "gsheet": GsheetTypeCasting.build_tree(),
        "calc": CalcTypeCasting.build_tree(),
    }
