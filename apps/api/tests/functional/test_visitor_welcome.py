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


def test_visitor_with_bad_name_is_told_what_to_fix_and_can_quote_a_reference():
    """
    Given the Canasta service is up,
    When a visitor introduces themselves with a name containing a forbidden
    character,
    Then the service explains the name is not acceptable, points at the name
    field, and gives a reference number that matches the one on the response,
    so support can trace the visit.
    """
    # Given
    client = TestClient(create_app(Settings(_env_file=None)))

    # When
    response = client.get("/api/v1/hello", params={"name": "a;b"})

    # Then
    error = response.json()["error"]
    assert response.status_code == 422
    assert error["message"]
    assert error["details"][0]["field"] == "name"
    assert error["request_id"] == response.headers["X-Request-ID"]

    # Clean
    client.close()
