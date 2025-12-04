from wizard.token.whitespace import Whitespace


def test_transform(spaces):
    for num, s in enumerate(Whitespace(spaces).transform(), 1):
        assert isinstance(s, Whitespace) and s.value == " " * num + spaces
