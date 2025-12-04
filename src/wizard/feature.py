from __future__ import annotations
from abc import ABC, abstractmethod
from collections import OrderedDict
import importlib
import sys
from typing import Self, Optional, Literal, Type
import re

from wizard.cell import Cell
from wizard.utils import ensure_str_cast

SOFTWARE_NAME: Optional[str] = None


def _import_libs(sn: str):
    """Loads all feature modules from folder software name(sn)."""
    global SOFTWARE_NAME
    SOFTWARE_NAME = sn

    module_name = f"{__package__}.features.{sn}"

    # remove old modules
    modules_to_remove = [
        k
        for k in sys.modules.keys()
        if k == module_name or k.startswith(module_name + ".")
    ]

    # Also remove classes from the registry before reloading modules
    if hasattr(AbstractFeature, "_registry"):
        classes_to_remove = [
            k
            for k, v in AbstractFeature._registry.items()
            if v.__module__.startswith(f"wizard.features.{sn}")
        ]
        for k in classes_to_remove:
            del AbstractFeature._registry[k]

    for mod_name in modules_to_remove:
        del sys.modules[mod_name]

    importlib.invalidate_caches()
    module = importlib.import_module(module_name)
    importlib.reload(module)


def _pre_check(sn: Optional[str] = None):
    if sn:
        _import_libs(sn)
    if not SOFTWARE_NAME:
        raise ValueError("Provide software name to invoke the function again")


def filter_and_transform_features(
    features: OrderedDict[str, Type[AbstractFeature]], sn: str
) -> OrderedDict[str, Type[AbstractFeature]]:
    """Filters features by software name and transforms the dictionary key, removing the __module__ to leave only the __qualname__."""
    features = {
        k.split(".")[-1]: v
        for k, v in features.items()
        if sn in v.__module__ or "wizard.features.common" in v.__module__
    }
    return features


# The __subclasses__ method is not reliably maintained in cases of dynamic imports,so we manage our own data structure to track subclasses.
def load_all_features(
    sn: Optional[str] = None,
) -> OrderedDict[str, Type[AbstractFeature]]:
    """Loads all features for software."""
    _pre_check(sn)
    return filter_and_transform_features(AbstractFeature.find_leaf_classes(), sn)


def load_features(sn: Optional[str] = None) -> OrderedDict[str, Type[Feature]]:
    """Finds all leaf classes of the Feature class."""
    _pre_check(sn)
    return filter_and_transform_features(Feature.find_leaf_classes(), sn)


def load_general_features(
    sn: Optional[str] = None,
) -> OrderedDict[str, Type[GeneralFeature]]:
    """Finds all leaf classes of the GeneralFeature class."""
    _pre_check(sn)
    return filter_and_transform_features(GeneralFeature.find_leaf_classes(), sn)


def load_discard_features(
    sn: Optional[str] = None,
) -> OrderedDict[str, Type[DiscardFeature]]:
    """Finds all leaf classes of the DiscardFeature class."""
    _pre_check(sn)
    return filter_and_transform_features(DiscardFeature.find_leaf_classes(), sn)


def load_weird_features(
    sn: Optional[str] = None,
) -> OrderedDict[str, Type[WeirdFeature]]:
    """Finds all leaf classes of the WeirdFeature class."""
    _pre_check(sn)
    return filter_and_transform_features(WeirdFeature.find_leaf_classes(), sn)


class AbstractFeature(ABC):
    """Abstract base class for recognizing strings with specific properties."""

    _registry = OrderedDict()

    def __init_subclass__(cls, **kwargs):
        """Registers all subclasses, enabling reliable dynamic reloading."""
        super().__init_subclass__(**kwargs)
        AbstractFeature._registry[cls.__qualname__] = cls

    PATTERN: Optional[re.Pattern] = None
    EXAMPLES: list[str] = []
    COUNTER_EXAMPLES: list[str] = []
    TYPE: Literal["Datetime", "Number", "Text", "Bool", "Error", "Weird", "Discard"] = (
        "Text"
    )

    @classmethod
    @abstractmethod
    def evaluate(cls, s: str) -> bool:
        pass

    @classmethod
    @ensure_str_cast
    def evaluate_cell(cls, cell: Cell) -> bool:
        return cls.evaluate(str(cell.content))

    @classmethod
    def find_leaf_classes(cls) -> OrderedDict[str, Type]:
        """
        Finds all leaf classes that are descendants of the base class using a reliable registry.
        This method is safe for dynamic module reloading because it uses a manually
        managed registry (`_registry`) and the reliable `issubclass()` check.
        `issubclass()` is reliable because it checks the class's static MRO (Method
        Resolution Order) inheritance chain, unlike the volatile `__subclasses__()`
        which can be inconsistent during reloads.
        """
        leaves = OrderedDict()
        all_registered_classes = list(AbstractFeature._registry.values())

        for current_cls in all_registered_classes:
            # For consistency, a class is not considered a leaf of itself.
            # We are looking for descendant leaves only.
            if current_cls is cls:
                continue

            # Ensure the class is a subclass of the one calling find_leaf_classes
            # (e.g., if called on Feature, only get Feature's leaf subclasses)
            if not issubclass(current_cls, cls):
                continue

            is_leaf = True
            # Check if any other registered class is a subclass of the current one
            for other_cls in all_registered_classes:
                if current_cls is not other_cls and issubclass(other_cls, current_cls):
                    is_leaf = False
                    break

            if is_leaf:
                # The original returned a dict keyed by __name__, so we do the same.
                # filter_and_transform_features will handle the rest.
                leaves[current_cls.__name__] = current_cls

        return leaves


class Feature(AbstractFeature):
    """A standard feature class for recognizing meaningful strings."""

    pass


class GeneralFeature(Feature):
    """A feature class designed for top-level features"""

    pass


class WeirdFeature(AbstractFeature):
    """A feature class for recognizing unusual strings with an inferable pattern."""

    TYPE = "Weird"


class DiscardFeature(AbstractFeature):
    """A feature class for marking strings with non-inferable patterns and discarding them."""

    TYPE = "Discard"
