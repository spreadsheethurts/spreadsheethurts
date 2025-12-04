from __future__ import annotations
from abc import abstractmethod
import inspect
import subprocess
from collections import defaultdict
from itertools import islice
import uuid
from enum import Enum, StrEnum, EnumMeta
from pathlib import Path
import json
from typing import (
    Any,
    Optional,
    Callable,
    Self,
    TypedDict,
    NotRequired,
    Dict,
    Union,
    Protocol,
)
from datetime import datetime

from wizard.feature import WeirdFeature, DiscardFeature
from wizard.typ import Bool, Text, Int, Float, DateTime, Weird, Discard


class AutoNextEnumMeta(EnumMeta):
    def __new__(metacls, name, bases, clsdict):
        has_members = any(
            not key.startswith("_") and not inspect.isfunction(value)
            for key, value in clsdict.items()
        )

        if has_members and "NEXT" not in clsdict:
            clsdict["NEXT"] = "NEXT"

        return super().__new__(metacls, name, bases, clsdict)


class AutoNextStrEnum(StrEnum, metaclass=AutoNextEnumMeta):
    """A string enum that automatically adds a NEXT member."""

    pass


class Feature(Protocol):
    @classmethod
    def evaluate(cls, s: str) -> Union[bool, StrEnum]:
        """Evaluate the input string and return a binary routing decision(bool) or a multi-branch routing decision(StrEnum)."""


class Event(Enum):
    START = "start"
    DECISION = "decision"
    END = "end"


class Type(Enum):
    DATETIME = "DateTime"
    NUMBER = "Number"
    BOOLEAN = "Boolean"
    TEXT = "Text"


def get_type(value: Any) -> Type:
    if isinstance(value, DateTime):
        return Type.DATETIME
    elif isinstance(value, Bool):
        return Type.BOOLEAN
    elif isinstance(value, (Int, Float)):
        return Type.NUMBER
    elif isinstance(value, Text):
        return Type.TEXT
    else:
        raise ValueError(f"Unknown type: {type(value)}")


class Trace(TypedDict):
    """A dictionary with predefined, static keys for trace data."""

    event: Event
    input: NotRequired[str]
    node: NotRequired[Node]
    decision: NotRequired[Union[bool, str]]
    output: NotRequired[Any]


class Node:
    """A node in the decision tree that makes a decision and traverses to the next node."""

    def __init__(self, name: str):
        self.name = name
        self.uid = uuid.uuid4()

    @abstractmethod
    def decide(self, s: str, observer: TreeObserver) -> Any:
        raise NotImplementedError

    def __repr__(self) -> str:
        return self.name


class TreeObserver:
    """An observer that records the decision events of a decision tree."""

    def __init__(self):
        self.events: list[Trace] = []

    def _record_event(
        self,
        event: Event,
        **kwargs,
    ):
        """Add a event and context after a node is visited."""
        data: Trace = {
            "event": event,
            **kwargs,
        }
        self.events.append(data)

    def record_decision(self, node: Node, decision: Union[bool, str]):
        """Record a routing decision from a node.

        Args:
            node: The branch node making the decision
            decision: The routing decision (bool for backward compatibility or string routing key)
        """
        self._record_event(Event.DECISION, node=node, decision=decision)

    def record_start(self, input: str):
        self._record_event(Event.START, input=input)

    def record_end(self, node: Node, output: Any):
        self._record_event(Event.END, node=node, output=output)

    def get_events(self) -> list[Trace]:
        return self.events

    def clear(self):
        self.events = []


class BranchNode(Node):
    """A branch node that makes a decision and traverses to the appropriate child based on feature evaluation."""

    def __init__(self, feature: Feature, children: Dict[str, Node]):
        super().__init__(feature.__qualname__)
        self.feature = feature
        self.children = children

    def decide(self, s: str, observer: TreeObserver, scalar: bool = False) -> Any:
        routing = str(self.feature.evaluate(s))
        if routing not in self.children:
            raise ValueError(
                f"Routing '{routing}' not found in {self.feature.__qualname__} children: {list(self.children.keys())}"
            )
        observer.record_decision(self, routing)
        return self.children[routing].decide(s, observer, scalar=scalar)


class LeafNode(Node):
    """A leaf node representing a type cluster in the input string space, associated with parsers.

    Args:
        typ: The expected type for inputs processed by this node.
        scalar_value_parser: Callable that converts an input string to a scalar value(int/float/str).
        cell_value_parser: Callable that converts an input string to a structured cell value(datetime/bool/str/float/int).
        examples: A list of examples that the leaf node can handle.
    """

    def __init__(
        self,
        typ: Type,
        scalar_value_parser: Callable[[str], Any],
        cell_value_parser: Callable[[str], Any],
        examples: Optional[list[str]] = None,
    ):
        super().__init__(cell_value_parser.__qualname__)
        self.typ = typ
        self.examples = examples or []
        self.scalar_value_parser = scalar_value_parser
        self.cell_value_parser = cell_value_parser

    def decide(
        self,
        s: str,
        observer: TreeObserver,
        scalar: bool = False,
        check_type: bool = False,
    ) -> Any:
        """Decide the type and value for the given input string.

        Args:
            s: The input string to parse.
            observer: Records conversion events and decisions.
            scalar: Whether to parse the input string as a scalar value or a cell value.
            check_type: Whether to validate the parsed type matches the expected type.
        """
        if check_type:
            value = self.cell_value_parser(s)
            typ = get_type(value)
            if typ != self.typ:
                raise ValueError(
                    f"Type mismatch: {typ} != {self.typ} for {s}\n full traces: {observer.get_events()}"
                )
            value = self.scalar_value_parser(s) if scalar else value
        else:
            value = self.scalar_value_parser(s) if scalar else self.cell_value_parser(s)

        self.examples.append(s)
        observer.record_end(self, value)
        return value

    @classmethod
    def text_node(cls, examples: Optional[list[str]] = None) -> Self:
        """A convenient helper to create a dummy leaf node that simply returns the input string."""
        return cls(Type.TEXT, lambda s: Text(s), lambda s: Text(s), examples)


class LeafNodeBuilder:
    """A builder for leaf nodes that provides default empty examples."""

    def __init__(self):
        self._examples: list[str] = None
        self._scalar_value_parser = None
        self._cell_value_parser = None
        self._typ = None

    def samples(self, samples: list[str]) -> Self:
        self._examples = samples
        return self

    def scalar_value_parser(self, parser: Callable[[str], Any]) -> Self:
        self._scalar_value_parser = parser
        return self

    def cell_value_parser(self, parser: Callable[[str], Any]) -> Self:
        self._cell_value_parser = parser
        return self

    def typ(self, typ: Type) -> Self:
        self._typ = typ
        return self

    def build(self) -> LeafNode:
        # typ and parser are required
        if self._typ is None:
            raise ValueError("Type is not set")
        if self._scalar_value_parser is None or self._cell_value_parser is None:
            raise ValueError("Parser is not set")
        return LeafNode(
            self._typ,
            self._scalar_value_parser,
            self._cell_value_parser,
            self._examples,
        )


class BranchNodeBuilder:
    """A builder for branch nodes that provides both binary and multi-branch support."""

    def __init__(self) -> None:
        self._feature = None
        self._children: Dict[str, Node] = {}

    def feature(self, feature: Feature) -> Self:
        self._feature = feature
        return self

    def on_true(self, node: Node) -> Self:
        """Set the true branch for binary routing."""
        self._children["True"] = node
        return self

    def on_false(self, node: Node) -> Self:
        """Set the false branch for binary routing."""
        self._children["False"] = node
        return self

    def branch(self, key: str, node: Node) -> Self:
        """Set a custom branch for multi-branch routing.

        Args:
            key: The routing key string (e.g., 'integer', 'float', 'date')
            node: The child node to route to when this key matches
        """
        self._children[key] = node
        return self

    def build(self) -> BranchNode:
        """Build a branch node that makes a decision based on a feature.

        For binary trees: automatically creates default branches if none are specified.
        For multi-branch trees: requires explicit branches to be set.

        The true branch's parsers are derived from the feature if not explicitly provided:
        - The `scalar_parser` uses the feature's `to_scalar_number` method, falling back to an identity parser if unavailable.
        - The `cell_parser` uses the feature's `to_cell_number` method, falling back to an identity parser if unavailable.

        The false branch defaults to a text leaf node if not specified.
        """
        if self._feature is None:
            raise ValueError("Feature is not set")

        is_binary = (
            "True" in self._children
            or "False" in self._children
            or self._children == {}
        )
        if is_binary:
            if "True" not in self._children:
                # Create default true branch
                scalar_parser = (
                    self._feature.to_scalar_number
                    if hasattr(self._feature, "to_scalar_number")
                    else lambda s: s
                )
                cell_parser = (
                    self._feature.to_cell_number
                    if hasattr(self._feature, "to_cell_number")
                    else lambda s: s
                )

                match self._feature.TYPE:
                    case "Datetime":
                        typ = Type.DATETIME
                    case "Bool":
                        typ = Type.BOOLEAN
                    case "Number":
                        typ = Type.NUMBER
                    case "Weird":
                        typ = Type.TEXT
                    case _:
                        typ = Type.TEXT
                self._children["True"] = (
                    LeafNodeBuilder()
                    .typ(typ)
                    .scalar_value_parser(scalar_parser)
                    .cell_value_parser(cell_parser)
                    .build()
                )

            if "False" not in self._children:
                self._children["False"] = LeafNode.text_node()

        return BranchNode(self._feature, self._children)

    @staticmethod
    def build_false_chain(*elements: type[Feature] | BranchNodeBuilder) -> BranchNode:
        """Build a branch node that chains multiple independent features or branch nodes.

        The chain follows: Each node's false branch continues to the next node, while true branches terminate in leaf nodes.
        """
        if not elements:
            raise ValueError("No feature or branch node provided")

        last = elements[-1]
        if isinstance(last, BranchNodeBuilder):
            last = last.build()
        else:
            last = BranchNodeBuilder().feature(last).build()

        node = last
        for ele in elements[::-1][1:]:
            if not isinstance(ele, BranchNodeBuilder):
                ele = BranchNodeBuilder().feature(ele)
            node = ele.on_false(node).build()
        return node


class DecisionTree:
    """A decision tree that acts as a type-casting process function by composing features and parsers to produce a final typed value.

    The tree maintains traces of its decision-making process for each input, which are useful for interpreting its behavior.
    """

    def __init__(
        self,
        root: Node,
        weird_features: Optional[list[WeirdFeature]] = None,
        discard_features: Optional[list[DiscardFeature]] = None,
    ):
        self.root = root
        self.observer = TreeObserver()
        self.traces: dict[str, list[Trace]] = {}
        self.weirds = (
            [BranchNodeBuilder().feature(f).build() for f in weird_features]
            if weird_features
            else []
        )
        self.discards = (
            [BranchNodeBuilder().feature(f).build() for f in discard_features]
            if discard_features
            else []
        )

    def decide(self, s: str, redecide: bool = False, scalar: bool = False) -> Any:
        """Evaluate the decision tree for the given input and return the final value.

        Args:
            input (str): The input to evaluate.
            redecide (bool, optional): Whether to reevaluate the input. Useful when debugging or refining the tree for a specific input.
            scalar (bool, optional): Whether to convert the cell value to a scalar value(int/float).
        """
        if redecide or s not in self.traces:

            for weird in self.weirds:
                self.observer.record_start(input=s)
                weird.decide(s, self.observer, scalar=scalar)
                self.traces[s] = self.observer.get_events()
                self.observer.clear()
                if self.traces[s][-2]["decision"] == "True":
                    return Weird(self.traces[s][-1]["output"])
                else:
                    self.traces.pop(s)

            self.observer.record_start(input=s)
            value = self.root.decide(s, self.observer, scalar=scalar)
            self.traces[s] = self.observer.get_events()
            self.observer.clear()

            # if the output value is s, then check if it is a discard
            if value == s:
                for discard in self.discards:
                    self.observer.record_start(input=s)
                    discard.decide(s, self.observer, scalar=scalar)
                    trace = self.observer.get_events()
                    self.observer.clear()
                    if trace[-2]["decision"] == "True":
                        self.traces[s] = trace
                        return Discard(trace[-1]["output"])
            return value
        else:
            return self.traces[s][-1]["output"]

    def get_trace(self, input: str) -> list[Trace]:
        """Get the trace of the decision tree for a evaluated input by `decide`."""
        return self.traces[input]

    def to_console(self) -> None:
        """Display the decision tree in the console using rich."""
        from rich.tree import Tree
        from rich import print as rprint

        def add_node(tree: Tree, node: Node) -> None:
            if isinstance(node, BranchNode):
                # Add all children with their routing keys
                for routing_key, child in node.children.items():
                    # Color code the routing key
                    if routing_key.lower() in ["true", "t"]:
                        color = "green"
                    elif routing_key.lower() in ["false", "f"]:
                        color = "red"
                    else:
                        color = "blue"

                    edge_label = child.name
                    child_tree = tree.add(f"[bold]{child.name}[/bold]")
                    child_tree.label = f"[{color}]{routing_key}[/{color}] {edge_label}\n{child_tree.label}"
                    add_node(child_tree, child)
            elif isinstance(node, LeafNode):
                tree.add(f"[blue]Leaf {node.typ.value}[/blue]")

        tree = Tree(f"[bold]{self.root.name}[/bold]")
        add_node(tree, self.root)
        rprint(tree)

    def to_svg(
        self,
        full: bool = True,
        trace: Optional[list[Trace]] = None,
        path: Path = Path("decision_tree.svg"),
    ):
        """Plot the decision tree with an optional trace highlighted. The trace should be generated by `get_trace`.

        Args:
            full (bool, optional): Whether to expand the tree to show all nodes. Defaults to True.
            trace (list[Trace], optional): Trace to highlight. Defaults to None.
            path (Path, optional): File path to save the SVG. Defaults to Path("decision_tree.svg").
        """

        def contains_weird(trace: list[Trace]) -> bool:
            if trace[-2]["node"] in self.weirds:
                return True
            return False

        def contains_discard(trace: list[Trace]) -> bool:
            if trace[-2]["node"] in self.discards:
                return True
            return False

        if not full and not trace:
            raise ValueError(
                "Invalid combination: if 'full' is False, 'traces' must be provided"
            )

        branches: dict[str, str] = {}  # uid -> name
        leaves: dict[str, dict[str, Any]] = defaultdict(dict)  # uid -> meta
        edges: dict[tuple[str, str], str] = {}  # (source, target) -> label
        highlights: set[str] = set()  # uid
        input: Optional[str] = None
        wl = [self.root]
        if trace:
            input = trace[0]["input"]
            highlights.update(str(t["node"].uid) for t in trace[1:])
            leaves[str(trace[-1]["node"].uid)]["output"] = repr(trace[-1]["output"])

            wl: list[Node] = (
                [self.root]
                if not contains_weird(trace) and not contains_discard(trace)
                else [trace[-2]["node"]]
            )

        visited: set[str] = set()
        # only expand untaken branches by one level when full is False
        one_level_expanded: set[str] = set()

        while wl:
            node = wl.pop(0)
            if node.uid in visited:
                continue
            visited.add(node.uid)

            is_traced_node = str(node.uid) in highlights

            if isinstance(node, BranchNode):
                branches[str(node.uid)] = node.name
                if full or node.uid not in one_level_expanded:
                    # Create edges for all children with their routing keys as labels
                    for routing_key, child in node.children.items():
                        edges[(str(node.uid), str(child.uid))] = routing_key

                        if is_traced_node and str(child.uid) not in highlights:
                            one_level_expanded.add(child.uid)
                        wl.append(child)  # type: ignore
            elif isinstance(node, LeafNode):
                leaves[str(node.uid)].update(
                    {
                        "typ": node.typ.value,
                        "examples": list(islice(node.examples, 3)),
                        "parser": node.cell_value_parser.__qualname__,
                    }
                )
        # branches:   A dictionary mapping branch node UIDs to their names.
        # leaves:     A dictionary mapping leaf node UIDs to their metadata.
        #             Includes 'examples', 'typ', 'parser', and an optional 'output'.
        # edges:      A dictionary mapping (source_uid, target_uid) tuples to their edge labels.
        # highlights: A set or list of node UIDs to be highlighted in the visualization.
        # input:      The initial input string for the entire process.
        data = {
            "branches": [{"uid": uid, "name": name} for uid, name in branches.items()],
            "leaves": [{"uid": uid, **meta} for uid, meta in leaves.items()],
            "edges": [
                {"source": source, "target": target, "label": label}
                for (source, target), label in edges.items()
            ],
            "highlights": list(highlights),
            "input": input,
        }

        # Custom JSON encoder to handle datetime objects
        class DateTimeEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, (datetime, datetime.date, datetime.time)):
                    return obj.strftime("%Y-%m-%d %H:%M:%S")
                return super().default(obj)

        # Execute the js script to generate the svg
        jstr = json.dumps(data, cls=DateTimeEncoder)

        render_script_path = Path(__file__).parent / "render_tree.js"
        try:
            result = subprocess.run(
                ["node", render_script_path, jstr],
                check=True,
                capture_output=True,
                text=True,
            )
            result.check_returncode()
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w") as f:
                f.write(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"Error generating tree visualization: {e}")
            print(f"Error output: {e.stderr}")

    def get_nodes(self, leaf: bool = False) -> list[Node]:
        """Get all nodes in the decision tree."""
        nodes = []
        visited = set()

        def dfs(node: Node):
            nonlocal nodes
            if node.uid in visited:
                return
            visited.add(node.uid)

            if isinstance(node, BranchNode):
                dfs(node.left)
                dfs(node.right)
                nodes.append(node)
            elif leaf:
                nodes.append(node)

        dfs(self.root)
        return nodes
