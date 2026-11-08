from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from canasta_api.main import create_app
from canasta_api.settings import Settings

pytestmark = pytest.mark.functional


def test_visitor_is_welcomed_by_name():
    """
    Given the Canasta service is up and healthy,
    When a visitor introduces themselves as Ana,
    Then the service greets them with "Welcome to Canasta, Ana!".
    """
    # Given
    client = TestClient(create_app(Settings(_env_file=None)))
    assert client.get("/api/v1/health").json()["status"] == "ok"

    # When
    response = client.get("/api/v1/hello", params={"name": "Ana"})

    # Then
    assert response.json()["message"] == "Welcome to Canasta, Ana!"

    # Clean
    client.close()
