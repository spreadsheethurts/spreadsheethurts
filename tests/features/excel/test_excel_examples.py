from wizard.feature import load_all_features, AbstractFeature


def test_examples():
    features: dict[str, AbstractFeature] = load_all_features("excel")
    for feature in features.values():
        for example in feature.EXAMPLES:
            assert feature.evaluate(example)

        for counter_example in feature.COUNTER_EXAMPLES:
            assert not feature.evaluate(counter_example)
