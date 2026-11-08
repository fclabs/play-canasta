"""Domain errors and their mapping to the FR-014 error envelope.

``AppError`` subclasses carry no HTTP knowledge; the status mapping lives in
``ERROR_STATUS`` below (handler layer, BR-005).
"""

from __future__ import annotations

from http import HTTPStatus
from typing import Any, ClassVar

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from canasta_api.schemas.errors import ErrorBody, ErrorEnvelope
from canasta_api.settings import INTERNAL_ERROR_MESSAGE

UNKNOWN_REQUEST_ID = "unknown"


class AppError(Exception):
    """Base of all domain errors. Subclass and set ``code``/``default_message``."""

    code: ClassVar[str] = "app_error"
    default_message: ClassVar[str] = "Application error"

    def __init__(
        self,
        message: str | None = None,
        *,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.details = details
        super().__init__(self.message)


class NotFoundError(AppError):
    code = "not_found"
    default_message = "Resource not found"


class ConflictError(AppError):
    code = "conflict"
    default_message = "Conflict with the current state"


# Handler-layer mapping; resolved along the MRO so subclasses inherit.
ERROR_STATUS: dict[type[AppError], int] = {
    NotFoundError: 404,
    ConflictError: 409,
}


def status_for(exc: AppError) -> int | None:
    """HTTP status registered for ``exc`` (nearest base class), or None."""
    for cls in type(exc).__mro__:
        for registered, status in ERROR_STATUS.items():
            if cls is registered:
                return status
    return None


def request_id_of(request: Request) -> str:
    value = request.scope.get("state", {}).get("request_id")
    return value if isinstance(value, str) else UNKNOWN_REQUEST_ID


def error_response(
    status_code: int,
    code: str,
    message: str,
    request_id: str,
    details: list[dict[str, Any]] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    envelope = ErrorEnvelope(
        error=ErrorBody(
            code=code, message=message, request_id=request_id, details=details
        )
    )
    return JSONResponse(
        envelope.model_dump(mode="json"), status_code=status_code, headers=headers
    )


def internal_error_response(request_id: str) -> JSONResponse:
    """Generic 500 envelope; never carries exception detail."""
    return error_response(500, "internal_error", INTERNAL_ERROR_MESSAGE, request_id)


async def handle_app_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    status = status_for(exc)
    if status is None:
        return internal_error_response(request_id_of(request))
    return error_response(
        status, exc.code, exc.message, request_id_of(request), exc.details
    )


async def handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    details: list[dict[str, Any]] = []
    for item in exc.errors():
        loc = [str(part) for part in item["loc"]]
        field = ".".join(loc[1:]) if len(loc) > 1 else ".".join(loc)
        details.append(
            {
                "field": field,
                "location": loc[0] if loc else "",
                "message": str(item["msg"]),
                "type": str(item["type"]),
            }
        )
    return error_response(
        422,
        "validation_error",
        "Request validation failed",
        request_id_of(request),
        details,
    )


_HTTP_CODES: dict[int, str] = {404: "not_found", 405: "method_not_allowed"}


async def handle_http_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    status = exc.status_code
    code = _HTTP_CODES.get(status, "http_error")
    try:
        message = HTTPStatus(status).phrase
    except ValueError:  # pragma: no cover - non-standard status
        message = "HTTP error"
    headers = dict(exc.headers) if exc.headers else None
    return error_response(
        status, code, message, request_id_of(request), headers=headers
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Install envelope handlers. Unhandled exceptions are handled by the
    request middleware (see ``logging.py``) so the header and log line survive."""
    app.add_exception_handler(AppError, handle_app_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_error)
