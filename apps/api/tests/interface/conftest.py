"""interface-layer fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from canasta_api.main import create_app
from canasta_api.settings import Settings


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


SECRET_TEXT = "TOP-SECRET-OUTSIDE-DIST"
INDEX_HTML = "<!doctype html><title>Canasta</title><div id=root></div>"


@pytest.fixture
def dist_dir(tmp_path: Path) -> Path:
    """Temp web bundle: ``dist/{index.html,assets/app.js}`` plus a secret file
    beside it (``secret.txt``) that must never be served."""
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text(INDEX_HTML)
    (dist / "assets" / "app.js").write_text("console.log('app');")
    (tmp_path / "secret.txt").write_text(SECRET_TEXT)
    return dist


@pytest.fixture
def static_client(dist_dir: Path) -> TestClient:
    """Client for an app serving ``dist_dir`` through ``WEB_DIST_DIR``."""
    settings = Settings(_env_file=None, WEB_DIST_DIR=dist_dir)
    return TestClient(create_app(settings))
