from wizard.token import Alphabet


def test_prefixes(alphas):
    alphabet = Alphabet(alphas)

    contain_self = False

    for length, prefix in enumerate(alphabet.prefixes(), 1):
        assert (
            isinstance(prefix, Alphabet)
            and len(prefix) == length
            and prefix.value in alphas
        )
        if prefix.value == alphas:
            contain_self = True

    assert contain_self


def test_transform(alphas):
    for alphabet in Alphabet(alphas).transform():
        assert isinstance(alphabet, Alphabet) and alphabet.value.isalpha()
