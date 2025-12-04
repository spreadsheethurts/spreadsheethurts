import random

import pytest

from wizard.token.tokenizer import Digit, Whitespace, Special, Alphabet


@pytest.mark.repeat(10)
def test_basic(tokenizer, alphas, digits, punctuations, spaces):
    letters_outcome = tokenizer(alphas)[0]
    digits_outcome = tokenizer(digits)[0]
    spaces_outcome = tokenizer(spaces)[0]
    punctuations_outcome = tokenizer(rf"{punctuations}")

    assert isinstance(letters_outcome, Alphabet) and letters_outcome.value == alphas
    assert isinstance(digits_outcome, Digit) and digits_outcome.value == digits
    assert isinstance(spaces_outcome, Whitespace) and spaces_outcome.value == spaces

    for idx, punctuation in enumerate(punctuations_outcome):
        assert (
            isinstance(punctuation, Special) and punctuation.value == punctuations[idx]
        )


@pytest.mark.repeat(10)
def test_mix(tokenizer, alphas, digits, punctuations, spaces):
    mixed = r"".join(
        random.choices(
            [alphas, digits, punctuations, spaces],
            k=random.randint(1, 100),
        )
    )
    tokens = tokenizer(mixed)

    idx = 0

    for token in tokens:
        if isinstance(token, Alphabet):
            assert not any(token.value.split(alphas))
        elif isinstance(token, Digit):
            assert not any(token.value.split(digits))
        elif isinstance(token, Whitespace):
            assert not any(token.value.split(spaces))
        elif isinstance(token, Special):
            assert token.value == punctuations[idx]
            idx = (idx + 1) % len(punctuations)
        else:
            raise AssertionError(f"Unknown token: {token}")
