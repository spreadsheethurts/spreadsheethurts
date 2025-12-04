from pytest import fixture

from wizard.argumentation.mutator.base import replace
from wizard.token import Token, Sequence, Digit


@fixture(scope="session")
def digits() -> str:
    return "2024/1/1 12:1:1.1111"


def test_replace_simple(digits):
    def replace_first(
        meta: Sequence[tuple[int, Token]]
    ) -> list[list[tuple[int, Token]]]:
        r: Sequence = meta.first()
        retvals = [[tuple(r.replace(1, Digit(str(i))))] for i in range(10)]
        return retvals

    def replace_last(meta: Sequence[tuple[int, Token]]):
        r: Sequence = meta.last()
        retvals = [[tuple(r.replace(1, Digit(str(i))))] for i in range(10)]
        return retvals

    def replace_all(meta: Sequence[tuple[int, Token]]):
        return [[(idx, Digit(str(i))) for idx, _ in meta] for i in range(10)]

    replacements = replace(digits, lambda x: x.isdigit(), replace_first)
    first_template = "{num}/1/1 12:1:1.1111"
    for idx, replacement in enumerate(replacements):
        assert replacement == first_template.format(num=idx)

    replacements = replace(digits, lambda x: x.isdigit(), replace_last)
    last_template = "2024/1/1 12:1:1.{num}"
    for idx, replacement in enumerate(replacements):
        assert replacement == last_template.format(num=idx)

    replacements = replace(digits, lambda x: x.isdigit(), replace_all)
    all_template = "{num}/{num}/{num} {num}:{num}:{num}.{num}"
    for idx, replacement in enumerate(replacements):
        assert replacement == all_template.format(num=idx)
