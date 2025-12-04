import pytest

from wizard.software.gsheet import Gsheet


class TestGsheet:

    @pytest.fixture
    def gsheet(self):
        return Gsheet()

    def test_evaluate_texts(self, gsheet: Gsheet):
        inputs = ["hello", "2", "True", "$2"]
        expected = ["hello", 2, True, 2]
        result = gsheet.evaluate_texts(inputs)
        assert result == expected
