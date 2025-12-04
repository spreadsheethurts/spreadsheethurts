from pathlib import Path

import pytest
import pandas as pd

from wizard.classifier import EquivalentClassChecker
from wizard.software import Excel


@pytest.fixture(scope="session")
def dummy_checker(sheet):
    excel = Excel("host", "port", Path("/tmp"), "single")
    return EquivalentClassChecker(excel, sheet)


def test_equivalence_check(
    dummy_checker: EquivalentClassChecker,
):
    input_decoding = pd.Series({"f1": True, "f2": False})
    output_decoding = pd.DataFrame(
        {
            "number": [True, False, False],
            "datetime": [False, False, True],
            "bool": [False, True, False],
            "error": [False, False, False],
            "string": [False, False, False],
        }
    )
    meta = dummy_checker._equivalence_check(
        input_decoding, output_decoding, sample=False
    )

    assert not meta.equivalent
    assert len(meta.cluster_sizes) == 2
