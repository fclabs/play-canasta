"""Meta-test: enforces the test-layer conventions (FR-040, FR-045, VC-040b)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

TESTS_DIR = Path(__file__).resolve().parent.parent
LAYERS = ("unit", "interface", "functional")
ERROR_CODES = ("validation_error", "not_found", "method_not_allowed", "internal_error")
REAL_CLOCK_CALLS = frozenset(
    {"now", "utcnow", "today", "time", "time_ns", "perf_counter", "monotonic", "sleep"}
)


def parse_layer(layer: str) -> dict[Path, ast.Module]:
    return {
        path: ast.parse(path.read_text(), filename=str(path))
        for path in sorted((TESTS_DIR / layer).glob("test_*.py"))
    }


def test_every_layer_has_test_files():
    for layer in LAYERS:
        assert parse_layer(layer), f"no test files under {layer}/"


@pytest.mark.parametrize("layer", LAYERS)
def test_layers_use_plain_functions_not_test_classes(layer: str):
    offenders = [
        f"{path.name}:{node.name}"
        for path, tree in parse_layer(layer).items()
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and node.name.startswith("Test")
    ]
    assert offenders == []


def test_unit_tests_import_no_test_client():
    offenders: list[str] = []
    for path, tree in parse_layer("unit").items():
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.ImportFrom):
                names = [node.module or "", *(a.name for a in node.names)]
            elif isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            if any("testclient" in n.lower() or n == "TestClient" for n in names):
                offenders.append(path.name)
    assert offenders == []


def test_unit_tests_call_no_real_clock():
    offenders: list[str] = []
    for path, tree in parse_layer("unit").items():
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr in REAL_CLOCK_CALLS:
                offenders.append(f"{path.name}:{node.lineno}")
    assert offenders == []


@pytest.mark.parametrize("code", ERROR_CODES)
def test_interface_tests_cover_each_error_code(code: str):
    covered = any(
        isinstance(node, ast.FunctionDef)
        and node.name.startswith("test_")
        and any(isinstance(c, ast.Constant) and c.value == code for c in ast.walk(node))
        for tree in parse_layer("interface").values()
        for node in ast.walk(tree)
    )
    assert covered, f"no interface test asserts error code {code!r}"


def test_functional_tests_use_real_create_app():
    trees = parse_layer("functional")
    for path, tree in trees.items():
        calls = [
            n
            for n in ast.walk(tree)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name)
            and n.func.id == "create_app"
        ]
        assert calls, f"{path.name} never calls create_app()"


def test_functional_tests_have_docstrings():
    missing = [
        f"{path.name}:{node.name}"
        for path, tree in parse_layer("functional").items()
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name.startswith("test_")
        and not ast.get_docstring(node)
    ]
    assert missing == []
