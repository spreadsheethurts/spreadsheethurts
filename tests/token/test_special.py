from wizard.token.special import Special
import string


def test_transform(punctuations):
    for punctuation in punctuations:
        for s in Special(punctuation).transform():
            assert isinstance(s, Special) and s.value in string.punctuation
