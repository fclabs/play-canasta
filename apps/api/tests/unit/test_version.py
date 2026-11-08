from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

import canasta_api

pytestmark = pytest.mark.unit

PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


def test_version_matches_pyproject_version():
    # Given the project metadata
    project = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]

    # When comparing with the package constant
    version = canasta_api.__version__

    # Then both agree
    assert version == project["version"]
