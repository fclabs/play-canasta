from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.interface


def test_hello_welcomes_named_player(client: TestClient):
    # Given / When
    response = client.get("/api/v1/hello", params={"name": "Ana"})

    # Then
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to Canasta, Ana!"}


def test_hello_defaults_to_player_when_name_omitted(client: TestClient):
    # Given / When
    response = client.get("/api/v1/hello")

    # Then
    assert response.json() == {"message": "Welcome to Canasta, player!"}


@pytest.mark.parametrize("name", ["José Núñez", "a", "x" * 40])
def test_hello_accepts_valid_names(client: TestClient, name: str):
    # Given / When
    response = client.get("/api/v1/hello", params={"name": name})

    # Then
    assert response.status_code == 200
    assert response.json() == {"message": f"Welcome to Canasta, {name}!"}


@pytest.mark.parametrize(
    "name", ["", "x" * 41, "<script>", "  ", "a;b"], ids=lambda n: repr(n)[:12]
)
def test_hello_rejects_invalid_names_with_422(client: TestClient, name: str):
    # Given / When
    response = client.get("/api/v1/hello", params={"name": name})

    # Then
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert error["message"]
    assert error["request_id"] == response.headers["X-Request-ID"]
    assert [d["field"] for d in error["details"]] == ["name"]
