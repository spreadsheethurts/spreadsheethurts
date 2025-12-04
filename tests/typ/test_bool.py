from wizard.typ import Bool, Int


class TestBool:
    def test_logical_operators(self):
        assert (Bool(True) and Bool(True)) == Bool(True)
        assert (Bool(False) and Bool(True)) == Bool(False)
        assert (Bool(False) and Bool(False)) == Bool(False)
        assert (Bool(True) or Bool(True)) == Bool(True)
        assert Bool(True)
        assert not Bool(False)

    def test_to_number(self):
        assert Bool(True).to_number() == Int(1)
        assert Bool(False).to_number() == Int(0)

    def test_repr(self):
        assert repr(Bool(True)) == "Bool(True)"
        assert repr(Bool(False)) == "Bool(False)"
