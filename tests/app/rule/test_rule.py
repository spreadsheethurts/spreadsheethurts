def test_large_integer(large_integer_test_cases, typecasting_rules):
    for software, test_cases in large_integer_test_cases.items():
        for input, expected in test_cases:
            assert typecasting_rules[software].decide(input) == expected
