from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from canasta_api.main import create_app
from canasta_api.settings import Settings

pytestmark = pytest.mark.interface

SECRET = "TOP-SECRET-OUTSIDE-DIST"


def test_root_serves_index_html(static_client: TestClient):
    # When
    response = static_client.get("/")

    # Then
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "<title>Canasta</title>" in response.text


def test_unknown_client_route_falls_back_to_index_html(static_client: TestClient):
    # When
    response = static_client.get("/game/xyz")

    # Then
    assert response.status_code == 200
    assert "<title>Canasta</title>" in response.text


def test_existing_asset_is_served_as_file(static_client: TestClient):
    # When
    response = static_client.get("/assets/app.js")

    # Then
    assert response.status_code == 200
    assert response.content == b"console.log('app');"


def test_directory_path_falls_back_to_index_html(static_client: TestClient):
    # When
    response = static_client.get("/assets")

    # Then
    assert response.status_code == 200
    assert "<title>Canasta</title>" in response.text


def test_api_routes_are_not_shadowed(static_client: TestClient):
    # When
    response = static_client.get("/api/v1/health")

    # Then
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.parametrize("path", ["/api/nope", "/api/v1/nope", "/api"])
def test_unknown_api_path_returns_envelope_not_html(
    static_client: TestClient, path: str
):
    # When
    response = static_client.get(path)

    # Then
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert "text/html" not in response.headers["content-type"]


@pytest.mark.parametrize(
    "path",
    [
        "/../secret.txt",
        "/%2e%2e/secret.txt",
        "/%2e%2e/%2e%2e/etc/passwd",
        "/assets/../../secret.txt",
        "/assets/%2e%2e/%2e%2e/secret.txt",
        "/%2e%2e%2fsecret.txt",
        "/..%2fsecret.txt",
        "/%00",
    ],
)
def test_path_traversal_never_serves_outside_files(
    static_client: TestClient, path: str
):
    # When
    response = static_client.get(path)

    # Then
    assert SECRET not in response.text
    assert response.status_code in (200, 404)
    if response.status_code == 200:
        assert "<title>Canasta</title>" in response.text


def test_unset_web_dist_dir_returns_404_envelope(client: TestClient):
    # When
    response = client.get("/")

    # Then
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_dist_dir_without_index_html_disables_static(tmp_path):
    # Given an existing directory with no index.html
    app = create_app(Settings(_env_file=None, WEB_DIST_DIR=tmp_path))

    # When
    response = TestClient(app).get("/")

    # Then
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_missing_dist_dir_disables_static(tmp_path):
    # Given a path that does not exist
    app = create_app(Settings(_env_file=None, WEB_DIST_DIR=tmp_path / "nope"))

    # When
    response = TestClient(app).get("/")

    # Then
    assert response.status_code == 404
