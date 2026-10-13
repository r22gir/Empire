"""AI desk registry is the single source of truth — 17 desks.

Loaded by file path so collection does not import the full MAX package.
"""
import ast
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "app/services/max/desks/desk_registry.py"
MANAGER_PATH = ROOT / "app/services/max/desks/desk_manager.py"


def _load_registry():
    spec = importlib.util.spec_from_file_location("desk_registry_isolated", REGISTRY_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _manager_desk_classes() -> list[str]:
    """Read the class names constructed in AIDeskManager.initialize()."""
    tree = ast.parse(MANAGER_PATH.read_text())
    names: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "AIDeskManager":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "initialize":
                    for stmt in item.body:
                        if isinstance(stmt, ast.Assign):
                            for target in stmt.targets:
                                if isinstance(target, ast.Name) and target.id == "desks":
                                    if isinstance(stmt.value, ast.List):
                                        for elt in stmt.value.elts:
                                            if isinstance(elt, ast.Call) and isinstance(elt.func, ast.Name):
                                                names.append(elt.func.id)
    return names


def test_canonical_count_is_seventeen():
    registry = _load_registry()
    assert registry.CANONICAL_DESK_COUNT == 17
    assert len(registry.REGISTERED_DESKS) == 17
    assert len(set(registry.registered_desk_ids())) == 17


def test_registry_payload_shape():
    payload = _load_registry().registry_payload()
    assert payload["source"] == "desk_registry"
    assert payload["count"] == 17
    ids = [d["id"] for d in payload["desks"]]
    assert "forge" in ids
    assert "codeforge" in ids
    assert "innovation" in ids


def test_manager_initialize_matches_registry():
    registry = _load_registry()
    class_names = _manager_desk_classes()
    assert len(class_names) == registry.CANONICAL_DESK_COUNT
    expected = [f"{d['name']}" for d in registry.REGISTERED_DESKS]
    assert class_names == expected
