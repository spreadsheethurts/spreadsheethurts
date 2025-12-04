import string
import random

import pytest

from wizard.token.tokenizer import Tokenizer


@pytest.fixture(scope="module")
def tokenizer():
    return Tokenizer()


@pytest.fixture(scope="function")
def alphas() -> str:
    return "".join(random.choices(string.ascii_letters, k=random.randint(2, 100)))


@pytest.fixture(scope="function")
def digits() -> str:
    return "".join(random.choices(string.digits, k=random.randint(1, 20)))


@pytest.fixture(scope="function")
def punctuations() -> str:
    return "".join(random.choices(string.punctuation, k=random.randint(1, 20)))


@pytest.fixture(scope="function")
def spaces() -> str:
    return "".join(random.choices(string.whitespace, k=random.randint(1, 20)))
