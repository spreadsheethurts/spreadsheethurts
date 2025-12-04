from wizard.token import Digit


def test_digit_operations(digits):
    digit = Digit(digits)

    operands = [
        1,
        1.0,
        -100000,
        100000,
        Digit("1"),
        Digit("10"),
        Digit("100000"),
    ]

    for operand in operands:
        assert isinstance(digit + operand, Digit)
        assert isinstance(operand + digit, Digit)
        assert isinstance(digit - operand, Digit)
        assert isinstance(operand - digit, Digit)
        assert isinstance(digit * operand, Digit)
        assert isinstance(operand * digit, Digit)
        assert isinstance(digit / operand, Digit)
        assert isinstance(operand / digit, Digit)
        assert isinstance(digit // operand, Digit)
        assert isinstance(operand // digit, Digit)
        assert isinstance(digit % operand, Digit)
        assert isinstance(operand % digit, Digit)


def test_digit_leading_zeros(digits):
    digit = Digit(digits)
    for num, d in enumerate(digit.leading_zeros(), 1):
        assert isinstance(d, Digit) and d.value.startswith("0" * num)


def test_transform(digits):
    for digit in Digit(digits).transform():
        assert isinstance(digit, Digit) and digit.value.isdigit()
