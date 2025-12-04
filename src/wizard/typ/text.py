class Text(str):
    """A string subclass that provides a custom class representation.

    Unlike Int/Float, Text does not override any methods which means it will return standard str objects when methods are called.
    """

    def __repr__(self) -> str:
        return f"Text({super().__repr__()})"
