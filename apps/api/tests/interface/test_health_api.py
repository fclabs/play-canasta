from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import canasta_api

pytestmark = pytest.mark.interface


def test_health_returns_ok_payload(client: TestClient):
    # Given the running app
    # When
    response = client.get("/api/v1/health")

    # Then
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {
        "status": "ok",
        "service": "canasta-api",
        "version": canasta_api.__version__,
    }
