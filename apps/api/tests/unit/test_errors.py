from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request

from canasta_api.errors import (
    AppError,
    ConflictError,
    NotFoundError,
    handle_app_error,
    handle_http_error,
    handle_validation_error,
    internal_error_response,
    register_exception_handlers,
    request_id_of,
    status_for,
)

pytestmark = pytest.mark.unit


class SpecificNotFound(NotFoundError):
    code = "specific_not_found"


class UnmappedError(AppError):
    code = "unmapped"


def make_request(request_id: str | None = "rid-1") -> Request:
    state = {"request_id": request_id} if request_id is not None else {}
    return Request({"type": "http", "state": state, "headers": []})


def body_of(response: Any) -> dict[str, Any]:
    return json.loads(response.body)


def test_app_error_uses_default_message_and_details_none():
    # Given / When
    exc = NotFoundError()

    # Then
    assert exc.message == "Resource not found"
    assert exc.details is None
    assert str(exc) == "Resource not found"


def test_app_error_accepts_custom_message_and_details():
    # Given / When
    exc = ConflictError("taken", details=[{"field": "x"}])

    # Then
    assert (exc.message, exc.details, exc.code) == (
        "taken",
        [{"field": "x"}],
        "conflict",
    )


@pytest.mark.parametrize(
    ("exc", "status"),
    [
        (NotFoundError(), 404),
        (SpecificNotFound(), 404),
        (ConflictError(), 409),
        (UnmappedError(), None),
    ],
)
def test_status_for_resolves_nearest_registered_base(exc, status):
    # Given / When / Then
    assert status_for(exc) == status


def test_handle_app_error_maps_domain_error_to_envelope():
    # Given
    exc = SpecificNotFound("no such player", details=[{"id": 7}])

    # When
    response = asyncio.run(handle_app_error(make_request(), exc))

    # Then
    assert response.status_code == 404
    assert body_of(response) == {
        "error": {
            "code": "specific_not_found",
            "message": "no such player",
            "request_id": "rid-1",
            "details": [{"id": 7}],
        }
    }


def test_handle_app_error_hides_unmapped_errors_as_500():
    # Given / When
    response = asyncio.run(handle_app_error(make_request(), UnmappedError("secret")))

    # Then
    assert response.status_code == 500
    assert body_of(response)["error"]["message"] == "Internal server error"
    assert b"secret" not in response.body


def test_handle_validation_error_lists_offending_fields():
    # Given
    exc = RequestValidationError(
        [
            {"type": "string_too_long", "loc": ("query", "name"), "msg": "too long"},
            {"type": "missing", "loc": ("body", "a", "b"), "msg": "required"},
            {"type": "x", "loc": (), "msg": "odd"},
        ]
    )

    # When
    response = asyncio.run(handle_validation_error(make_request(), exc))

    # Then
    error = body_of(response)["error"]
    assert response.status_code == 422
    assert error["code"] == "validation_error"
    assert error["message"]
    assert [d["field"] for d in error["details"]] == ["name", "a.b", ""]
    assert error["details"][0]["location"] == "query"


@pytest.mark.parametrize(
    ("status", "code", "message"),
    [
        (404, "not_found", "Not Found"),
        (405, "method_not_allowed", "Method Not Allowed"),
        (403, "http_error", "Forbidden"),
    ],
)
def test_handle_http_error_maps_status_to_code(status, code, message):
    # Given
    exc = StarletteHTTPException(status, headers={"Allow": "GET"})

    # When
    response = asyncio.run(handle_http_error(make_request(), exc))

    # Then
    assert response.status_code == status
    assert body_of(response)["error"]["code"] == code
    assert body_of(response)["error"]["message"] == message
    assert response.headers["allow"] == "GET"


def test_handle_http_error_without_headers():
    # Given / When
    response = asyncio.run(
        handle_http_error(make_request(), StarletteHTTPException(404))
    )

    # Then
    assert "allow" not in response.headers


def test_internal_error_response_is_generic():
    # Given / When
    response = internal_error_response("rid-9")

    # Then
    assert response.status_code == 500
    assert body_of(response) == {
        "error": {
            "code": "internal_error",
            "message": "Internal server error",
            "request_id": "rid-9",
            "details": None,
        }
    }


def test_request_id_of_falls_back_to_unknown():
    # Given / When / Then
    assert request_id_of(make_request("abc")) == "abc"
    assert request_id_of(make_request(None)) == "unknown"


def test_register_exception_handlers_installs_three_handlers():
    # Given
    app = FastAPI()

    # When
    register_exception_handlers(app)

    # Then
    assert {AppError, RequestValidationError, StarletteHTTPException} <= set(
        app.exception_handlers
    )
