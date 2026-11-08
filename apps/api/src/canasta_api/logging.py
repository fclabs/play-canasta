"""Request-ID and wide-event request logging (FR-015, FR-016)."""

from __future__ import annotations

import json
import logging
import re
import sys
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from time import perf_counter
from typing import Any

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from canasta_api.errors import internal_error_response
from canasta_api.settings import (
    REQUEST_ID_HEADER,
    REQUEST_ID_PATTERN,
    REQUEST_LOG_EVENT,
    REQUEST_LOGGER_NAME,
    SERVICE_NAME,
)

_REQUEST_ID_RE = re.compile(REQUEST_ID_PATTERN)
FIELDS_ATTR = "event_fields"


def utc_now() -> datetime:
    return datetime.now(UTC)


def new_uuid() -> str:
    return str(uuid.uuid4())


class JsonFormatter(logging.Formatter):
    """One JSON object per line: level, event (message) and the wide fields."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {}
        fields = getattr(record, FIELDS_ATTR, None)
        if isinstance(fields, dict):
            payload.update(fields)
        payload["level"] = record.levelname
        payload["event"] = record.getMessage()
        return json.dumps(payload, default=str, ensure_ascii=False)


class StdoutHandler(logging.Handler):
    """Writes to the *current* ``sys.stdout`` (so capture/mocking works)."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            sys.stdout.write(self.format(record) + "\n")
            sys.stdout.flush()
        except Exception:  # noqa: BLE001
            self.handleError(record)


def configure_logging(level: str) -> None:
    """Idempotently attach the JSON stdout handler to the request logger."""
    logger = logging.getLogger(REQUEST_LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False
    if not any(isinstance(h, StdoutHandler) for h in logger.handlers):
        handler = StdoutHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)


def resolve_request_id(inbound: str | None, factory: Callable[[], str]) -> str:
    if inbound is not None and _REQUEST_ID_RE.fullmatch(inbound):
        return inbound
    return factory()


def outcome_for(status_code: int) -> tuple[str, int]:
    """Return (outcome, logging level) for a status code."""
    if status_code >= 500:
        return "server_error", logging.ERROR
    if status_code >= 400:
        return "client_error", logging.WARNING
    return "ok", logging.INFO


class RequestContextMiddleware:
    """Pure ASGI middleware: request ID, X-Request-ID header, one log line,
    and the 500 envelope for unhandled exceptions. Must be the outermost
    user middleware so every response (incl. 404/405/422) is covered."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        env: str,
        clock: Callable[[], datetime] = utc_now,
        timer: Callable[[], float] = perf_counter,
        uuid_factory: Callable[[], str] = new_uuid,
    ) -> None:
        self.app = app
        self.env = env
        self.clock = clock
        self.timer = timer
        self.uuid_factory = uuid_factory
        self.logger = logging.getLogger(REQUEST_LOGGER_NAME)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        inbound: str | None = None
        for key, value in scope.get("headers", []):
            if key.lower() == REQUEST_ID_HEADER.lower().encode("latin-1"):
                inbound = value.decode("latin-1")
                break
        request_id = resolve_request_id(inbound, self.uuid_factory)
        scope.setdefault("state", {})["request_id"] = request_id

        started_at = self.timer()
        status_code = 500
        response_started = False
        error_type: str | None = None

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code, response_started
            if message["type"] == "http.response.start":
                response_started = True
                status_code = message["status"]
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
            await send(message)

        try:
            try:
                await self.app(scope, receive, send_wrapper)
            except Exception as exc:
                error_type = type(exc).__name__
                if response_started:
                    raise
                await internal_error_response(request_id)(scope, receive, send_wrapper)
        finally:
            self._log(scope, request_id, status_code, started_at, error_type)

    def _log(
        self,
        scope: Scope,
        request_id: str,
        status_code: int,
        started_at: float,
        error_type: str | None,
    ) -> None:
        outcome, level = outcome_for(status_code)
        fields: dict[str, Any] = {
            "timestamp": self.clock().astimezone(UTC).isoformat(),
            "service": SERVICE_NAME,
            "env": self.env,
            "request_id": request_id,
            "method": scope["method"],
            "path": scope["path"],
            "status_code": status_code,
            "latency_ms": max(0.0, round((self.timer() - started_at) * 1000, 3)),
            "outcome": outcome,
        }
        if error_type is not None:
            fields["error_type"] = error_type
        self.logger.log(level, REQUEST_LOG_EVENT, extra={FIELDS_ATTR: fields})
