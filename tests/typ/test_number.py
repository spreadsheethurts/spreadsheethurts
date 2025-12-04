from wizard.typ.number import Int, Float
from wizard.typ.text import Text
from wizard.typ.datetime.gregoriandatetime import GregorianDateTime


class TestNumber:
    def test_arithmetic(self):
        assert Int(1) + Int(2) == Int(3)
        assert Float(1.0) + Float(2.0) == Float(3.0)
        assert Int(1) - Float(2.0) == Float(-1.0)
        assert Float(1.0) - Int(2) == Float(-1.0)
        assert Int(1) * Int(2) == Int(2)
        assert Float(1.0) * Float(2.0) == Float(2.0)
        assert Int(1) / Int(2) == Float(0.5)
        assert Float(1.0) / Float(2.0) == Float(0.5)
        assert Int(1) % Int(2) == Int(1)
        assert Float(1.0) % Float(2.0) == Float(1.0)
        assert Int(1) ** Int(2) == Int(1)

    def test_eq(self):
        assert Int(1) == Float(1.0)
        assert Float(6687618.832719675) == 6687618.832719676 and not (
            6687618.832719676 != Float(6687618.832719675)
        )

class TestCrossTypeEquality:
    def test_int_float_equality(self):
        assert Int(1) == 1
        assert Int(1) == 1.0
        assert Float(1.0) == 1
        assert Float(1.0) == 1.0
        assert Int(1) == Float(1.0)
        assert Float(1.0) == Int(1)

        assert not (Int(1) != 1)
        assert not (Int(1) != 1.0)
        assert not (Float(1.0) != 1)
        assert not (Float(1.0) != 1.0)
        assert not (Int(1) != Float(1.0))
        assert not (Float(1.0) != Int(1))

    def test_number_text_inequality(self):
        assert Int(1) != Text("1")
        assert Text("1") != Int(1)
        assert Float(1.0) != Text("1.0")
        assert Text("1.0") != Float(1.0)

        assert not (Int(1) == Text("1"))
        assert not (Text("1") == Int(1))
        assert not (Float(1.0) == Text("1.0"))
        assert not (Text("1.0") == Float(1.0))

    def test_number_datetime_inequality(self):
        dt = GregorianDateTime(2024, 1, 1)
        assert Int(1) != dt
        assert dt != Int(1)
        assert Float(1.0) != dt
        assert dt != Float(1.0)

        assert not (Int(1) == dt)
        assert not (dt == Int(1))
        assert not (Float(1.0) == dt)
        assert not (dt == Float(1.0))

    def test_text_datetime_inequality(self):
        dt = GregorianDateTime(2024, 1, 1)
        text = Text("2024-01-01")
        assert text != dt
        assert dt != text

        assert not (text == dt)
        assert not (dt == text)