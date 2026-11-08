from __future__ import annotations

import re
import uuid
from collections.abc import Callable
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from canasta_api.errors import ConflictError, NotFoundError
from canasta_api.main import create_app
from canasta_api.services.hello import build_welcome_message
from canasta_api.settings import Settings

pytestmark = pytest.mark.interface

ENVELOPE_KEYS = {"code", "message", "request_id", "details"}


class PlayerNotFoundError(NotFoundError):
    code = "player_not_found"
    default_message = "Player not found"


def assert_envelope(response: Any, status: int, code: str) -> dict[str, Any]:
    assert response.status_code == status
    body = response.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == ENVELOPE_KEYS
    assert body["error"]["code"] == code
    assert body["error"]["request_id"] == response.headers["X-Request-ID"]
    return body["error"]


def test_unknown_api_path_returns_404_not_found_envelope(client: TestClient):
    # Given / When
    response = client.get("/api/v1/nope")

    # Then
    error = assert_envelope(response, 404, "not_found")
    assert error["details"] is None


def test_unknown_top_level_api_path_returns_404_envelope(client: TestClient):
    # Given / When
    response = client.get("/api/nope")

    # Then
    assert_envelope(response, 404, "not_found")


def test_post_to_health_returns_405_method_not_allowed_envelope(client: TestClient):
    # Given / When
    response = client.post("/api/v1/health")

    # Then
    assert_envelope(response, 405, "method_not_allowed")
    assert "GET" in response.headers["Allow"]


def test_invalid_name_returns_422_validation_envelope_naming_field(
    client: TestClient,
):
    # Given / When
    response = client.get("/api/v1/hello", params={"name": "a;b"})

    # Then
    error = assert_envelope(response, 422, "validation_error")
    assert error["message"]
    assert [d["field"] for d in error["details"]] == ["name"]


def test_unhandled_exception_returns_generic_500_without_leaking(app: FastAPI):
    # Given
    def boom() -> None:
        raise RuntimeError("secret-detail")

    app.add_api_route("/api/v1/_boom", boom)
    client = TestClient(app, raise_server_exceptions=False)

    # When
    response = client.get("/api/v1/_boom")

    # Then
    error = assert_envelope(response, 500, "internal_error")
    assert error["message"] == "Internal server error"
    assert "secret-detail" not in response.text
    assert "Traceback" not in response.text

    # Clean
    client.close()


def test_app_error_from_service_maps_to_http_status(app: FastAPI):
    # Given
    def find_player(name: str) -> str:  # service-like function, no HTTP
        if name == "ghost":
            raise PlayerNotFoundError(details=[{"field": "name"}])
        if name == "dup":
            raise ConflictError()
        return build_welcome_message(name)

    app.add_api_route("/api/v1/_player", find_player)
    client = TestClient(app, raise_server_exceptions=False)

    # When
    missing = client.get("/api/v1/_player", params={"name": "ghost"})
    conflict = client.get("/api/v1/_player", params={"name": "dup"})
    fine = client.get("/api/v1/_player", params={"name": "Ana"})

    # Then
    error = assert_envelope(missing, 404, "player_not_found")
    assert error["message"] == "Player not found"
    assert error["details"] == [{"field": "name"}]
    assert_envelope(conflict, 409, "conflict")
    assert fine.status_code == 200

    # Clean
    client.close()


def test_inbound_valid_request_id_is_echoed(client: TestClient):
    # Given / When
    response = client.get("/api/v1/health", headers={"X-Request-ID": "abc-123"})

    # Then
    assert response.headers["X-Request-ID"] == "abc-123"


@pytest.mark.parametrize("bad", ["bad id!", "x" * 65])
def test_invalid_request_id_is_replaced_with_uuid4(client: TestClient, bad: str):
    # Given / When
    response = client.get("/api/v1/health", headers={"X-Request-ID": bad})

    # Then
    value = response.headers["X-Request-ID"]
    assert value != bad
    assert uuid.UUID(value).version == 4


def test_missing_request_id_is_generated_as_uuid4(client: TestClient):
    # Given / When
    response = client.get("/api/v1/health")

    # Then
    assert uuid.UUID(response.headers["X-Request-ID"]).version == 4


def test_error_envelope_carries_inbound_request_id(client: TestClient):
    # Given / When
    response = client.get("/api/nope", headers={"X-Request-ID": "trace.me_1"})

    # Then
    assert response.json()["error"]["request_id"] == "trace.me_1"


@pytest.mark.parametrize(
    ("path", "method", "status", "level", "outcome"),
    [
        ("/api/v1/health", "GET", 200, "INFO", "ok"),
        ("/api/v1/nope", "GET", 404, "WARNING", "client_error"),
        ("/api/v1/_boom", "GET", 500, "ERROR", "server_error"),
    ],
)
def test_one_wide_event_line_per_request(
    app: FastAPI,
    log_lines: Callable[[], list[dict[str, Any]]],
    path: str,
    method: str,
    status: int,
    level: str,
    outcome: str,
):
    # Given
    def boom() -> None:
        raise RuntimeError("secret-detail")

    app.add_api_route("/api/v1/_boom", boom)
    client = TestClient(app, raise_server_exceptions=False)
    log_lines()

    # When
    response = client.request(method, path)

    # Then
    (line,) = log_lines()
    assert line["event"] == "http_request"
    assert line["level"] == level
    assert line["outcome"] == outcome
    assert line["status_code"] == status
    assert line["method"] == method
    assert line["path"] == path
    assert line["env"] == "local"
    assert line["request_id"] == response.headers["X-Request-ID"]
    assert isinstance(line["latency_ms"], (int, float)) and line["latency_ms"] >= 0
    assert re.match(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d.*\+00:00$", line["timestamp"])

    # Clean
    client.close()


def test_log_line_never_contains_query_values(
    client: TestClient, capsys: pytest.CaptureFixture[str]
):
    # Given / When
    client.get("/api/v1/hello", params={"name": "Ana"})

    # Then
    out = capsys.readouterr().out
    assert out.count("\n") == 1
    assert "Ana" not in out


def test_log_env_reflects_app_env(
    log_lines: Callable[[], list[dict[str, Any]]],
):
    # Given
    client = TestClient(create_app(Settings(_env_file=None, APP_ENV="production")))
    log_lines()

    # When
    client.get("/api/v1/health")

    # Then
    assert log_lines()[0]["env"] == "production"

    # Clean
    client.close()
