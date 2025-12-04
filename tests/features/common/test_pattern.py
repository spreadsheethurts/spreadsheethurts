from wizard.features.common.pattern import Composite, Primitive


def test_binary_operations():
    p1 = Primitive("abc")
    p2 = Primitive("def")
    p3 = Primitive("ghi")
    group = (p1 + p2 + p3).group()
    assert group.__regex_str__() == Composite.sequence(p1, p2, p3).__regex_str__()

    branch = (p1 | p2 | p3).group()
    assert branch.__regex_str__() == Composite.branch(p1, p2, p3).__regex_str__()

    assert (group | branch | p3).__regex_str__() == Composite.branch(
        p1 + p2 + p3, p1 | p2 | p3, p3
    ).__regex_str__()

    assert (group + branch + p3).join_both_ends(
        p1
    ).__regex_str__() == Composite.sequence(
        p1, p1 + p2 + p3, p1, p1 | p2 | p3, p1, p3, p1
    ).__regex_str__()

    assert (
        group + branch + p3
    ).surround_anyspace().__regex_str__() == Composite.sequence(
        Primitive.anyspace(), p1 + p2 + p3, p1 | p2 | p3, p3, Primitive.anyspace()
    ).__regex_str__()
