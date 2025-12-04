import tempfile
import sys
import shutil
from pathlib import Path
import pytest

from wizard.feature import load_all_features


class FeatureTestHelper:
    """Helper class for creating and managing test features."""

    @staticmethod
    def remove_feature_file(directory, name):
        """Remove a feature file."""
        (directory / f"{name.lower()}.py").unlink()
        # unimport the feature
        init_path = directory / "__init__.py"
        init_content = init_path.read_text()
        init_content = init_content.replace(f"from .{name.lower()} import {name}", "")
        init_path.write_text(init_content)

    @staticmethod
    def create_feature_file(directory, name, examples, evaluate_pattern):
        """Create a feature file with given parameters."""
        content = f'''
from wizard.feature import Feature

class {name}(Feature):
    """Test feature {name}."""
    EXAMPLES = {examples}
    COUNTER_EXAMPLES = ["not_{name.lower()}"]
    TYPE = "Text"

    @classmethod
    def evaluate(cls, s: str) -> bool:
        return "{evaluate_pattern}" in s
'''
        (directory / f"{name.lower()}.py").write_text(content.strip())

    @staticmethod
    def update_init_file(directory, feature_names):
        """Update __init__.py to import specified features."""
        imports = [f"from .{name.lower()} import {name}" for name in feature_names]
        (directory / "__init__.py").write_text("\n".join(imports))

    @staticmethod
    def modify_feature_examples(directory, name, new_examples):
        """Modify a feature's EXAMPLES attribute."""
        file_path = directory / f"{name.lower()}.py"
        content = file_path.read_text()

        # Find and replace EXAMPLES line
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if line.strip().startswith("EXAMPLES = "):
                lines[i] = f"    EXAMPLES = {repr(new_examples)}"
                break
        new_content = "\n".join(lines)

        file_path.write_text(new_content.strip())

    @staticmethod
    def modify_feature_evaluate(directory, name, new_pattern):
        """Modify a feature's evaluate method pattern."""
        file_path = directory / f"{name.lower()}.py"
        content = file_path.read_text()

        # Find and replace evaluate pattern
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if 'return "' in line and '" in s' in line:
                lines[i] = f'        return "{new_pattern}" in s'
                break
        new_content = "\n".join(lines)

        file_path.write_text(new_content.strip())

    @staticmethod
    def verify_feature_properties(feature, expected_examples, expected_pattern):
        """Verify that a feature has the expected properties."""
        assert feature.EXAMPLES == expected_examples
        assert feature.evaluate(f"contains {expected_pattern}")
        assert not feature.evaluate("something completely different")

    @staticmethod
    def create_basic_features(directory):
        """Create a set of basic test features."""
        FeatureTestHelper.create_feature_file(
            directory, "TestFeature1", ["test1"], "test1"
        )
        FeatureTestHelper.create_feature_file(
            directory, "TestFeature2", ["test2"], "test2"
        )
        FeatureTestHelper.update_init_file(directory, ["TestFeature1", "TestFeature2"])

        return load_all_features("test_software")


@pytest.fixture
def temp_test_software():
    """Create a temporary test_software module with complete structure."""
    temp_dir = tempfile.mkdtemp()
    software_dir = Path(temp_dir) / "test_software"
    software_dir.mkdir()

    # Create __init__.py
    (software_dir / "__init__.py").write_text("")

    # Mock the package structure
    import wizard.features

    original_path = wizard.features.__path__

    try:
        # Temporarily add our test directory to the features path
        wizard.features.__path__.insert(0, str(software_dir.parent))

        yield software_dir

    finally:
        # Restore original path
        wizard.features.__path__ = original_path

        # Clean up modules we might have loaded
        modules_to_remove = [k for k in sys.modules.keys() if "test_software" in k]
        for mod in modules_to_remove:
            del sys.modules[mod]

        # Clean up temp directory
        shutil.rmtree(temp_dir)


class TestDynamicFeatureLoading:
    """Test dynamic feature loading functionality."""

    def test_basic_dynamic_loading(self, temp_test_software):
        """Test basic dynamic loading with temporary test_software."""
        # Use helper to create basic features
        features = FeatureTestHelper.create_basic_features(temp_test_software)

        # Verify basic functionality
        assert len(features) == 2
        assert "TestFeature1" in features
        assert "TestFeature2" in features

        # Use helper to verify feature properties
        FeatureTestHelper.verify_feature_properties(
            features["TestFeature1"], ["test1"], "test1"
        )
        FeatureTestHelper.verify_feature_properties(
            features["TestFeature2"], ["test2"], "test2"
        )

    def test_feature_modification(self, temp_test_software):
        """Test that reload works correctly after modifying a feature."""
        import inspect

        # Create initial feature file
        original_features = FeatureTestHelper.create_basic_features(temp_test_software)
        original_class = original_features["TestFeature1"]
        original_source = inspect.getsource(original_class)
        original_examples = original_class.EXAMPLES
        del original_class

        # Modify the feature
        FeatureTestHelper.modify_feature_examples(
            temp_test_software, "TestFeature1", ["modified_test1"]
        )
        FeatureTestHelper.modify_feature_evaluate(
            temp_test_software, "TestFeature1", "modified_test1"
        )

        # Reload features
        modified_features = load_all_features("test_software")
        modified_class = modified_features["TestFeature1"]
        modified_source = inspect.getsource(modified_class)
        modified_examples = modified_class.EXAMPLES

        # Verify changes were detected
        assert modified_examples != original_examples
        assert modified_examples == ["modified_test1"]
        assert modified_source != original_source

        # Test that the evaluate method also changed behavior
        assert not modified_class.evaluate("contains original_test1")
        assert modified_class.evaluate("contains modified_test1")

    def test_feature_addition(self, temp_test_software):
        """Tests that reload works correctly after adding a new feature."""
        # First, create and load two features
        FeatureTestHelper.create_feature_file(
            temp_test_software, "TestFeature1", ["test1"], "test1"
        )
        FeatureTestHelper.create_feature_file(
            temp_test_software, "TestFeature2", ["test2"], "test2"
        )
        FeatureTestHelper.update_init_file(
            temp_test_software, ["TestFeature1", "TestFeature2"]
        )
        features = load_all_features("test_software")
        assert len(features) == 2

        # Now, add a third feature and reload
        FeatureTestHelper.create_feature_file(
            temp_test_software, "TestFeature3", ["test3"], "test3"
        )
        FeatureTestHelper.update_init_file(
            temp_test_software, ["TestFeature1", "TestFeature2", "TestFeature3"]
        )

        features = load_all_features("test_software")
        assert len(features) == 3

    def test_reload_with_hierarchy_addition(self, temp_test_software):
        """
        Tests that find_leaf_classes works correctly after reloading with a new, complex inheritance hierarchy.
        """
        # 1. Initial state: Load basic features
        base_dir = temp_test_software
        initial_features = FeatureTestHelper.create_basic_features(base_dir)
        assert len(initial_features) == 2
        assert "TestFeature1" in initial_features
        assert "TestFeature2" in initial_features

        # 2. Addition: Define a new hierarchy and add it to the filesystem.
        (base_dir / "rootfeature.py").write_text(
            "from wizard.feature import Feature\nclass RootFeature(Feature):\n    @classmethod\n    def evaluate(cls, s: str) -> bool: return 'root' in s"
        )
        (base_dir / "branchafeature.py").write_text(
            "from .rootfeature import RootFeature\nclass BranchAFeature(RootFeature):\n    @classmethod\n    def evaluate(cls, s: str) -> bool: return 'branch_a' in s"
        )
        (base_dir / "leafa1feature.py").write_text(
            "from .branchafeature import BranchAFeature\nclass LeafA1Feature(BranchAFeature):\n    @classmethod\n    def evaluate(cls, s: str) -> bool: return 'leaf_a1' in s"
        )
        (base_dir / "leafa2feature.py").write_text(
            "from .branchafeature import BranchAFeature\nclass LeafA2Feature(BranchAFeature):\n    @classmethod\n    def evaluate(cls, s: str) -> bool: return 'leaf_a2' in s"
        )
        (base_dir / "branchbfeature.py").write_text(
            "from .rootfeature import RootFeature\nclass BranchBFeature(RootFeature):\n    @classmethod\n    def evaluate(cls, s: str) -> bool: return 'branch_b' in s"
        )

        # Update __init__.py to include BOTH old and new features
        feature_names = [
            "TestFeature1",
            "TestFeature2",
            "RootFeature",
            "BranchAFeature",
            "LeafA1Feature",
            "LeafA2Feature",
            "BranchBFeature",
        ]
        FeatureTestHelper.update_init_file(base_dir, feature_names)

        # 3. Reload: This will trigger cleanup and re-import of the whole 'test_software' module
        reloaded_features = load_all_features("test_software")

        # Assert that all leaf features are now loaded
        assert (
            len(reloaded_features) == 5
        )  # TestFeature1, TestFeature2, LeafA1, LeafA2, BranchB

        # 4. Assert: Perform the leaf-finding assertions on the reloaded state.
        from wizard.feature import AbstractFeature, Feature

        registry = AbstractFeature._registry

        def get_class_from_registry(name):
            for cls_obj in registry.values():
                if cls_obj.__name__ == name:
                    return cls_obj
            raise NameError(f"Class {name} not found in registry")

        RootFeature_class = get_class_from_registry("RootFeature")
        BranchAFeature_class = get_class_from_registry("BranchAFeature")
        LeafA1Feature_class = get_class_from_registry("LeafA1Feature")
        BranchBFeature_class = get_class_from_registry("BranchBFeature")

        # --- Assertions ---
        # 1. From Feature: Should find all leaves of the Feature branch, including
        # the original basic features and the new hierarchy's leaves.
        feature_leaves = Feature.find_leaf_classes()
        expected_leaves = {
            "GeneralFeature",
            "TestFeature1",
            "TestFeature2",
            "LeafA1Feature",
            "LeafA2Feature",
            "BranchBFeature",
        }
        assert set(feature_leaves.keys()) == expected_leaves

        # 2. From RootFeature
        root_leaves = RootFeature_class.find_leaf_classes()
        assert set(root_leaves.keys()) == {
            "LeafA1Feature",
            "LeafA2Feature",
            "BranchBFeature",
        }

        # 3. From BranchAFeature
        branch_a_leaves = BranchAFeature_class.find_leaf_classes()
        assert set(branch_a_leaves.keys()) == {"LeafA1Feature", "LeafA2Feature"}

        # 4. From BranchBFeature (which is a leaf)
        branch_b_leaves = BranchBFeature_class.find_leaf_classes()
        assert set(branch_b_leaves.keys()) == set()

        # 5. From a leaf
        leaf_a1_leaves = LeafA1Feature_class.find_leaf_classes()
        assert set(leaf_a1_leaves.keys()) == set()
