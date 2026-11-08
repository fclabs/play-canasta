from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.routing import Route

pytestmark = pytest.mark.interface


def test_openapi_document_lists_both_endpoints(client: TestClient):
    # Given / When
    response = client.get("/api/openapi.json")

    # Then
    body = response.json()
    assert response.status_code == 200
    assert body["openapi"].startswith("3.")
    assert "/api/v1/health" in body["paths"]
    assert "/api/v1/hello" in body["paths"]


def test_docs_page_is_served_as_html(client: TestClient):
    # Given / When
    response = client.get("/api/docs")

    # Then
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_all_routes_live_under_api_prefix(app: FastAPI):
    # Given the app's route table
    paths = [r.path for r in app.routes if isinstance(r, Route)]

    # When / Then
    assert paths
    assert all(p.startswith("/api") for p in paths)


def test_unprefixed_v1_path_is_not_found(client: TestClient):
    # Given / When
    response = client.get("/v1/health")

    # Then
    assert response.status_code == 404
