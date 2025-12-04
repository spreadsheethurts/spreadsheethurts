from wizard.token.base import Sequence


def test_append():
    stream = Sequence(range(10))
    stream = stream.append(10).append(11).append(12)
    assert list(stream) == list(range(13))


def test_insert():
    stream = Sequence(range(10))
    stream = stream.insert(0, -1).insert(10, 10)
    assert list(stream) == [-1, *range(9), 10, 9]
    stream = stream.insert(lambda x: x == -1, -2).insert(lambda x: x == 10, 11)
    assert list(stream) == [-2, -1, *range(9), 11, 10, 9]


def test_replace():
    stream = Sequence(range(10))
    stream = stream.replace(0, -1).replace(9, 10)
    assert list(stream) == [-1, *range(1, 9), 10]
    stream = stream.replace(lambda x: x == -1, -2).replace(lambda x: x == 10, 11)
    assert list(stream) == [-2, *range(1, 9), 11]


def test_remove():
    stream = Sequence(range(10))
    stream = stream.remove(0).remove(8)
    assert list(stream) == list(range(1, 9))
    stream = stream.remove(lambda x: x == 1).remove(lambda x: x == 8)
    assert list(stream) == list(range(2, 8))
