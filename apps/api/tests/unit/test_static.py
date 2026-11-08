from __future__ import annotations

from pathlib import Path

import pytest

from canasta_api.static import is_api_path, is_servable_dist, resolve_asset

pytestmark = pytest.mark.unit


@pytest.fixture
def dist(tmp_path: Path) -> Path:
    root = tmp_path / "dist"
    (root / "assets").mkdir(parents=True)
    (root / "index.html").write_text("x")
    (root / "assets" / "app.js").write_text("y")
    (tmp_path / "secret.txt").write_text("s")
    return root


@pytest.mark.parametrize(
    ("path", "expected"),
    [("/api", True), ("/api/v1/x", True), ("/apix", False), ("/", False)],
)
def test_is_api_path(path: str, expected: bool):
    assert is_api_path(path) is expected


def test_is_servable_dist_requires_index_html(tmp_path: Path, dist: Path):
    assert is_servable_dist(dist) is True
    assert is_servable_dist(tmp_path) is False
    assert is_servable_dist(None) is False


def test_resolve_asset_returns_existing_file(dist: Path):
    assert resolve_asset(dist, "assets/app.js") == (dist / "assets/app.js").resolve()


@pytest.mark.parametrize(
    "relative", ["missing.js", "assets", "../secret.txt", "assets/../../secret.txt"]
)
def test_resolve_asset_rejects_non_files_and_traversal(dist: Path, relative: str):
    assert resolve_asset(dist, relative) is None


def test_resolve_asset_rejects_null_bytes(dist: Path):
    assert resolve_asset(dist, "a\x00b") is None


def test_resolve_asset_rejects_symlink_escaping_dist(dist: Path):
    # Given a symlink inside dist pointing at a file outside
    (dist / "link.txt").symlink_to(dist.parent / "secret.txt")

    # Then it is not served
    assert resolve_asset(dist, "link.txt") is None
