from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

SERVICES_DIR = Path(__file__).resolve().parents[2] / "src" / "canasta_api" / "services"
FORBIDDEN = {"fastapi", "starlette"}


def _imported_roots(path: Path) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def test_services_import_no_http_framework():
    # Given every module under services/
    modules = sorted(SERVICES_DIR.glob("*.py"))

    # When collecting their imports
    offenders = {m.name: _imported_roots(m) & FORBIDDEN for m in modules}

    # Then none imports fastapi or starlette (BR-005)
    assert modules
    assert {name: bad for name, bad in offenders.items() if bad} == {}
