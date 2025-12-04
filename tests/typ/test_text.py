from wizard.typ.text import Text


class TestText:
    def test_equality_with_str(self):
        assert Text("hello") == "hello"
        assert "hello" == Text("hello")
        assert Text("hello") == Text("hello")

    def test_equality_with_special_chars(self):
        # Test with single quotes
        string_with_single_quote = "it's a test"
        assert Text(string_with_single_quote) == string_with_single_quote

        # Test with double quotes
        string_with_double_quote = 'a "quoted" string'
        assert Text(string_with_double_quote) == string_with_double_quote

        # Test with backticks
        string_with_backtick = "a `backticked` string"
        assert Text(string_with_backtick) == string_with_backtick

        assert Text("55.)#") == "55.)#"

        # Test with all of them
        complex_string = "it's a `complex` string"
        assert Text(complex_string) == complex_string

    def test_inequality(self):
        assert Text("hello") != "world"
        assert "world" != Text("hello")
        assert Text("hello") != Text("world")

    def test_repr(self):
        assert repr(Text("hello")) == "Text('hello')"
        assert repr(Text("it's a test")) == "Text(\"it's a test\")"