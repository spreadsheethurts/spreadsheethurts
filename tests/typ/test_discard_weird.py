import pytest
from wizard.typ import Int, Float, Text, Discard, Weird
from wizard.typ.datetime import (
    DateTime,
    GsheetDateTime,
    GregorianDateTime,
    ExcelDateTime,
)


class TestDiscardWeirdEquality:
    """Test that Discard and Weird are always equal to all other types"""

    # fmt: off
    @pytest.mark.parametrize("other_type", [
        # Number types
        Int(0), Int(1), Int(-1), Int(999),
        Float(0.0), Float(1.5), Float(-1.5), Float(float('inf')), Float(float('nan')),

        # String types
        Text(""), Text("hello"), Text("special!@#$%"),

        # DateTime types
        DateTime(2023, 1, 1), DateTime(1, 1, 1),
        GsheetDateTime(15000, 12, 25), GsheetDateTime(1, 1, 1),
        ExcelDateTime(1900, 1, 1), ExcelDateTime(1900, 2, 29),
        GregorianDateTime(1582, 10, 4), GregorianDateTime(1500, 2, 29),

        # Built-in types
        0, 1, -1, 3.14, "hello", "", None, True, False,

        # Complex objects
        [1, 2, 3], {"key": "value"}, object(), lambda x: x,

        # Discard Type
        Discard("anything"), Discard(1), Discard(Int(1)),

        # Weird Type
        Weird("anything"), Weird(1), Weird(Int(1)),
    ])
    # fmt: on
    def test_discard_equals_all_types(self, other_type):
        """Test Discard instances are equal to all types"""
        discard_val = Discard("anything")
        weird_val = Weird("anything")
        assert discard_val == other_type
        assert other_type == discard_val
        assert discard_val == weird_val
        assert weird_val == discard_val
