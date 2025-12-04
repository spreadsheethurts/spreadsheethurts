from __future__ import annotations
import re
from abc import ABC, abstractmethod
from copy import deepcopy
from types import UnionType
from typing import Self, Optional

from rich.tree import Tree

try:
    Primitive
except NameError:
    uid_update_history: dict[str, str] = {}

    class Pattern(ABC):
        name2id = {}

        def __init__(
            self,
            name: Optional[str] = None,
            quantifiers: Optional[list[str]] = None,
        ):
            self.name = name
            self.quantifiers = quantifiers or []

        @property
        def name(self):
            return self._name

        @name.setter
        def name(self, value: Optional[str]):
            """Update the name and uid simultaneously."""
            if value:
                self.name2id[value] = self.name2id.get(value, 0) + 1
                self._name = value
                self.uid = value + "_" + str(self.name2id[value])
            else:
                self._name = None
                self.uid = None

        def __repr__(self) -> str:
            if self.uid:
                return f"{self.__class__.__name__}(uid={self.uid})"
            else:
                return f"{self.__class__.__name__}()"

        @abstractmethod
        def clone(self, name: Optional[str] = None) -> Self:
            """Deep copy and update the uid of the current object."""

        @abstractmethod
        def __regex_str__(self) -> str:
            """Return the regex string representation of the current object."""

        def maybe(self) -> Self:
            """Append a '?' quantifier to make the pattern optional."""
            return self.__class__(deepcopy(self), quantifiers=["?"])

        def some(self) -> Self:
            """Append a '+' quantifier to make the pattern match at least once."""
            return self.__class__(deepcopy(self), quantifiers=["+"])

        def any(self) -> Self:
            """Append a '*' quantifier to make the pattern match any times."""
            return self.__class__(deepcopy(self), quantifiers=["*"])

        def repeat(self, n: int) -> Self:
            """Append a '{n}' quantifier to repeat exactly n times."""
            return self.__class__(deepcopy(self), quantifiers=[f"{{{n}}}"])

        def repeat_min(self, min: int) -> Self:
            """Append a '{min,}' quantifier to repeat at least min times."""
            return self.__class__(deepcopy(self), quantifiers=[f"{{{min},}}"])

        def repeat_max(self, max: int) -> Self:
            """Append a '{,max}' quantifier to repeat at most max times."""
            return self.__class__(deepcopy(self), quantifiers=[f"{{,{max}}}"])

        def repeat_range(self, min: int, max: int) -> Self:
            """Append a '{min,max}' quantifier to repeat between min and max times."""
            return self.__class__(deepcopy(self), quantifiers=[f"{{{min},{max}}}"])

        def compile(self) -> re.Pattern:
            return re.compile(self.__regex_str__())

        def named(self, name: Optional[str]) -> Self:
            """Update the name of the current object."""
            obj = deepcopy(self)
            obj.name = name
            return obj

        def backref(self) -> BackRef:
            """Return a backreference to the current object."""
            if self.uid:
                return BackRef(self.uid)
            else:
                raise ValueError(
                    "Pattern is not named, use `named` to set a name first."
                )

    class BackRef:
        def __init__(self, uid: str) -> None:
            self.uid = uid

        def clone(self, *args) -> Self:
            return self

        def __regex_str__(self) -> str:
            return f"(?P={self.uid})"

    class _Primitive:
        def __init__(self, regex: str | _Primitive) -> None:
            self.regex = regex

        @classmethod
        def empty(cls) -> Self:
            return cls("")

        @classmethod
        def space(cls) -> Self:
            return cls(" ")

        @classmethod
        def anyspace(cls) -> Self:
            return cls(r" *")

        @classmethod
        def somespace(cls) -> Self:
            return cls(r" +")

        @classmethod
        def digit(cls) -> Self:
            return cls(r"\d")

        @classmethod
        def digits(cls) -> Self:
            return cls(r"\d+")

        @classmethod
        def letter(cls) -> Self:
            return cls(r"[a-zA-Z]")

        @classmethod
        def letters(cls) -> Self:
            return cls(r"[a-zA-Z]+")

        @classmethod
        def exponent(cls) -> Self:
            return cls(r"[eE]")

        @classmethod
        def colon(cls) -> Self:
            return cls(":")

        @classmethod
        def slash(cls) -> Self:
            return cls("/")

        @classmethod
        def hyphen(cls) -> Self:
            return cls("-")

        @classmethod
        def minus(cls) -> Self:
            return cls(r"-")

        @classmethod
        def dollar(cls) -> Self:
            return cls(r"\$")

        @classmethod
        def plus(cls) -> Self:
            return cls(r"\+")

        @classmethod
        def dot(cls) -> Self:
            return cls(r"\.")

        @classmethod
        def comma(cls) -> Self:
            return cls(",")

        @classmethod
        def apm(cls) -> Self:
            return cls(r"[apAP][mM]")

    class Primitive(Pattern, _Primitive):
        """A primitive pattern that matches a specific string.

        Quantifiers are applied to the pattern sequentially based on their order
        of appearance. For instance, if `regex="a"` and `quantifiers=["{3}", "*"]`,
        the resulting regular expression is equivalent to `(a{3})*`.
        """

        def __init__(
            self,
            regex: str | Primitive,
            name: Optional[str] = None,
            quantifiers: Optional[list[str]] = None,
        ):
            _Primitive.__init__(self, regex)
            Pattern.__init__(self, name, quantifiers)

        def __repr__(self) -> str:
            if self.uid:
                return f"{self.__class__.__name__}(uid={self.uid})"
            else:
                return f"{self.__class__.__name__}(regex={self.regex})"

        def __regex_str__(self) -> str:
            regex = (
                self.regex.__regex_str__()
                if isinstance(self.regex, Primitive)
                else self.regex
            )
            for quantifier in self.quantifiers:
                regex = "(" + regex + ")" + quantifier
            return f"(?P<{self.uid}>{regex})" if self.uid else regex

        def __add__(self, other: Pattern | str | Placeholder | BackRef) -> Composite:
            other = String(other) if isinstance(other, str) else other
            if isinstance(other, Composite):
                return other.__radd__(self)
            else:
                return Composite.sequence(deepcopy(self), deepcopy(other))

        def __or__(self, other: Pattern | str | Placeholder | BackRef) -> Composite:
            other = String(other) if isinstance(other, str) else other
            if isinstance(other, Composite):
                return other.__ror__(self)
            else:
                return Composite.branch(deepcopy(self), deepcopy(other))

        def __radd__(self, other: str | BackRef | Placeholder) -> Composite:
            other = String(other) if isinstance(other, str) else other
            return Composite.sequence(deepcopy(other), deepcopy(self))

        def __ror__(self, other: str | BackRef | Placeholder) -> Composite:
            other = String(other) if isinstance(other, str) else other
            return Composite.branch(deepcopy(other), deepcopy(self))

        def clone(self, name: Optional[str] = None) -> Self:
            regex = (
                self.regex.clone() if isinstance(self.regex, Primitive) else self.regex
            )
            obj = self.__class__(regex, name or self.name, self.quantifiers)
            if self.uid:
                uid_update_history[self.uid] = obj.uid
            return obj

    class String(Primitive):
        """A pattern class without name that matches a specific string."""

        def __init__(
            self,
            regex: str | Primitive,
            name: Optional[str] = None,
            quantifiers: Optional[list[str]] = None,
        ):
            super().__init__(regex, name, quantifiers)

        def clone(self, *args) -> Self:
            return self

        def __add__(self, other: Pattern | str | Placeholder | BackRef) -> Composite:
            # Make linter happy to infer the return type
            return super().__add__(other)

        def __or__(self, other: Pattern | str | Placeholder | BackRef) -> Composite:
            # Make linter happy to infer the return type
            return super().__or__(other)

        def __radd__(self, other: str | BackRef | Placeholder) -> Composite:
            # Make linter happy to infer the return type
            return super().__radd__(other)

        def __ror__(self, other: str | BackRef | Placeholder) -> Composite:
            # Make linter happy to infer the return type
            return super().__ror__(other)

    class Placeholder:
        """A placeholder object used to define templates that can be replaced with actual patterns during formatting."""

        def __init__(self, name: str) -> None:
            self.name = name

        def clone(self, *args) -> Self:
            return self

        def __add__(self, other) -> Composite:
            return other.__radd__(self)

        def __or__(self, other) -> Composite:
            return other.__ror__(self)

        def __radd__(self, other) -> Composite:
            # Make linter happy to infer the return type
            raise NotImplementedError(f"{other} should implement __add__")

        def __ror__(self, other) -> Composite:
            # Make linter happy to infer the return type
            raise NotImplementedError(f"{other} should implement __or__")

        def __rich__(self):
            return self.name

    class Composite(Pattern):
        """An immutable composite pattern that enables building complex patterns through recursive composition.

        The pattern can be constructed in two ways:
        1. As a sequence - combining primitive and composite patterns in order
        2. As branches - providing multiple alternative patterns to match

        In addition to patterns, sequences can include:
        -   Placeholder objects: Act as templates that get replaced with actual patterns during formatting
        -   String objects (or raw strings): Define literal text to match without any special processing
            when using the Python tokenizer

        """

        def __init__(
            self,
            *args: Pattern | Placeholder | str | BackRef,
            name: Optional[str] = None,
            quantifiers: Optional[list[str]] = None,
            branch: bool = False,
            group: bool = False,
        ):
            self.is_branch = branch
            self.is_group = group
            self.regexes = [
                String(arg) if isinstance(arg, str) else arg for arg in args
            ]
            self._patterns = list(
                filter(lambda x: type(x) in (Primitive, Composite), self.regexes)
            )
            super().__init__(name, quantifiers)

        def patterns(self) -> list[Pattern]:
            """Return the primitive and composite patterns in the current object."""
            return self._patterns

        def __regex_str__(self) -> str:
            """Return the regex string representation of the current object."""
            if self.is_group:
                regex = self.regexes[0].__regex_str__()
                for quantifier in self.quantifiers:
                    regex = "(" + regex + ")" + quantifier
                return f"(?P<{self.uid}>{regex})" if self.uid else f"({regex})"

            if self.is_branch:
                regex = (
                    "("
                    + "|".join(
                        map(lambda x: "(" + x.__regex_str__() + ")", self.regexes)
                    )
                    + ")"
                )
            else:
                regex = "".join(map(lambda x: x.__regex_str__(), self.regexes))
            for quantifier in self.quantifiers:
                regex = "(" + regex + ")" + quantifier
            return f"(?P<{self.uid}>{regex})" if self.uid else regex

        def group(self, name: Optional[str] = None, quantifiers: Optional[list[str]] = None) -> Self:
            return self.__class__(self, group=True, name=name, quantifiers=quantifiers)

        @classmethod
        def branch(
            cls, *args: Pattern | Placeholder | str, name: Optional[str] = None, quantifiers: Optional[list[str]] = None
        ) -> Self:
            return cls(*args, name=name, branch=True, quantifiers=quantifiers)

        @classmethod
        def sequence(
            cls, *args: Pattern | Placeholder | str, name: Optional[str] = None, quantifiers: Optional[list[str]] = None
        ) -> Self:
            return cls(*args, name=name, branch=False, quantifiers=quantifiers)

        def clone(self, name: Optional[str] = None) -> Self:
            """Construct a new instance that updates the uid."""

            def _clone_each(maybe_pattern):
                if isinstance(maybe_pattern, Pattern):
                    obj = maybe_pattern.clone()
                    if maybe_pattern.uid:
                        uid_update_history[maybe_pattern.uid] = obj.uid
                    return obj
                elif isinstance(maybe_pattern, BackRef):
                    # Since we're doing a depth-first traversal, the referenced uid must already be updated.
                    # Otherwise, it is user's fault.
                    uid = uid_update_history[maybe_pattern.uid]
                    return BackRef(uid)
                else:
                    return maybe_pattern

            return self.__class__(
                *map(_clone_each, self.regexes),
                name=name or self.name,
                branch=self.is_branch,
                quantifiers=self.quantifiers,
            )

        def find(self, uid: str) -> Optional[Pattern]:
            """Find a pattern with the specified unique ID."""

            for pattern in self.patterns():
                if pattern.uid == uid:
                    return pattern
                elif isinstance(pattern, Composite):
                    result = pattern.find(uid)
                    if result:
                        return result
            return None

        def __rich__(self) -> Tree:
            """Return a rich tree representation of the composite pattern."""

            def traverse(tree: Tree, regexes: Self):
                """Traverse the composite pattern and add nodes to the tree."""

                markup_tree = "b bright_cyan" if regexes.is_branch else "cyan"
                color_leaf = "b bright_green" if regexes.is_branch else "green"

                for child in regexes.regexes:
                    if isinstance(child, Composite):
                        subtree = tree.add(f"[{markup_tree}]{child.uid}[/]")
                        traverse(subtree, child)
                    elif isinstance(child, Primitive):
                        tree.add(f"[{color_leaf}]{child.uid}[/]")
                    else:
                        tree.add(f"[bright_white]{child}")

            tree = Tree(f"[b bright_cyan]{self.uid}[/]")
            traverse(tree, self)

            return tree

        def format(self, **kwargs) -> Self:
            """Replace placeholder in the current object with specified patterns.

            This method differentiates based on the type of object:
            - For a multiple branch pattern, the method searches all branches with the same name and replaces their patterns recursively.
            - For a single sequence pattern, only the first occurrence of the pattern with the specified name is replaced.
            """
            if self.is_group:
                return self.regexes[0].format(**kwargs).group(self.quantifiers)

            if self.is_branch:
                id2pattern = {}
                for idx, branch in enumerate(self.regexes):
                    if isinstance(branch, Composite):
                        new_branch = branch.format(**kwargs)
                        id2pattern[idx] = new_branch
                if id2pattern:
                    patterns = deepcopy(self.regexes)
                    for idx, pattern in id2pattern.items():
                        patterns[idx] = pattern

                    return self.branch(*patterns, name=self.name, quantifiers=self.quantifiers)
                else:
                    raise ValueError(f"Template {kwargs.keys()} not found in {self}")
            else:
                tidxes = []
                for name in kwargs.keys():
                    for idx, pat in enumerate(self.regexes):
                        if isinstance(pat, Placeholder) and pat.name == name:
                            tidxes.append(idx)

                if tidxes:
                    patterns = deepcopy(self.regexes)
                    for tid, pattern in zip(tidxes, kwargs.values()):
                        patterns[tid] = pattern

                    return self.sequence(*patterns, name=self.name, quantifiers=self.quantifiers)
                else:
                    raise ValueError(f"Template {kwargs.keys()} not found in {self}")

        def __add__(self, other: Pattern | Placeholder | str | BackRef | Self) -> Self:
            if self.is_branch or self.is_group:
                return self.sequence(self, other)
            else:
                return self.sequence(*map(deepcopy, self.regexes), other)

        def __radd__(self, other: Pattern | Placeholder | str | BackRef | Self) -> Self:
            if self.is_branch or self.is_group:
                return self.sequence(other, self)
            else:
                return self.sequence(other, *map(deepcopy, self.regexes))

        def __or__(self, other: Pattern | Placeholder | str | BackRef | Self) -> Self:
            if self.is_branch:
                return self.branch(*map(deepcopy, self.regexes), other)
            else:
                return self.branch(self, other)

        def __ror__(self, other: Pattern | Placeholder | str | BackRef | Self) -> Self:
            return self.branch(other, self)

        def join(self, sep: Pattern | str) -> Self:
            """Join patterns with a separator."""
            if self.is_branch:
                raise ValueError("Cannot join branch patterns.")

            sep = String(sep) if isinstance(sep, str) else sep

            regexes = []
            for i, regex in enumerate(self.regexes):
                regexes.append(deepcopy(regex))
                if i < len(self.regexes) - 1:
                    regexes.append(sep)
            return self.sequence(*regexes)

        def join_with_head(self, sep: Pattern | str) -> Self:
            """Join patterns with separator and add separator at the start."""
            sep = String(sep) if isinstance(sep, str) else sep
            obj = self.join(sep)
            return self.sequence(sep, *obj.regexes)

        def join_with_tail(self, sep: Pattern | str) -> Self:
            """Join patterns with separator and add separator at the end."""
            sep = String(sep) if isinstance(sep, str) else sep
            obj = self.join(sep)
            return self.sequence(*obj.regexes, sep)

        def join_both_ends(self, sep: Pattern | str) -> Self:
            """Join patterns with separator and add separator at both start and end."""
            sep = String(sep) if isinstance(sep, str) else sep
            obj = self.join(sep)
            return self.sequence(sep, *obj.regexes, sep)

        def surround(self, sep: Pattern | str) -> Self:
            """Surround the current object with another pattern."""
            if self.is_branch:
                raise ValueError("Cannot surround branch patterns.")

            sep = String(sep) if isinstance(sep, str) else sep
            return self.sequence(sep, *map(deepcopy, self.regexes), sep)

        def surround_anyspace(self) -> Self:
            """Surround the current object with anyspace."""
            return self.surround(Primitive.anyspace())
