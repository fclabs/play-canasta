from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any

import pytest
from starlette.types import Message, Receive, Scope, Send

from canasta_api.logging import (
    JsonFormatter,
    RequestContextMiddleware,
    StdoutHandler,
    configure_logging,
    outcome_for,
    resolve_request_id,
)

pytestmark = pytest.mark.unit

FIXED_ID = "00000000-0000-4000-8000-000000000000"


def make_app(status: int = 200, raises: Exception | None = None):
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        if raises is not None:
            raise raises
        await send({"type": "http.response.start", "status": status, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    return app


def call(
    middleware: RequestContextMiddleware,
    path: str = "/api/x",
    headers: list[tuple[bytes, bytes]] | None = None,
) -> tuple[list[Message], Scope]:
    sent: list[Message] = []
    scope: Scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "query_string": b"name=Ana",
        "headers": headers or [],
    }

    async def receive() -> Message:
        return {"type": "http.request"}

    async def send(message: Message) -> None:
        sent.append(message)

    asyncio.run(middleware(scope, receive, send))
    return sent, scope


def build(
    app: Any,
    clock: Callable[[], datetime],
    timer: Callable[[], float],
    uuid_factory: Callable[[], str],
    env: str = "preview",
) -> RequestContextMiddleware:
    configure_logging("INFO")
    return RequestContextMiddleware(
        app, env=env, clock=clock, timer=timer, uuid_factory=uuid_factory
    )


def header(sent: list[Message], name: str) -> str | None:
    for key, value in sent[0]["headers"]:
        if key.decode().lower() == name.lower():
            return value.decode()
    return None


@pytest.mark.parametrize(
    ("inbound", "expected"),
    [
        ("abc-123", "abc-123"),
        ("A.b_c-9", "A.b_c-9"),
        ("x" * 64, "x" * 64),
        ("x" * 65, FIXED_ID),
        ("bad id!", FIXED_ID),
        ("", FIXED_ID),
        ("abc\n", FIXED_ID),
        (None, FIXED_ID),
    ],
)
def test_resolve_request_id_accepts_valid_and_replaces_invalid(inbound, expected):
    # Given / When
    result = resolve_request_id(inbound, lambda: FIXED_ID)

    # Then
    assert result == expected


@pytest.mark.parametrize(
    ("status", "outcome", "level"),
    [
        (200, "ok", logging.INFO),
        (399, "ok", logging.INFO),
        (400, "client_error", logging.WARNING),
        (404, "client_error", logging.WARNING),
        (499, "client_error", logging.WARNING),
        (500, "server_error", logging.ERROR),
    ],
)
def test_outcome_for_maps_status_to_outcome_and_level(status, outcome, level):
    # Given / When / Then
    assert outcome_for(status) == (outcome, level)


def test_middleware_logs_one_wide_event_for_ok_response(
    fixed_clock, fake_timer, fixed_uuid, log_lines
):
    # Given
    mw = build(make_app(200), fixed_clock, fake_timer, fixed_uuid)

    # When
    sent, _ = call(mw)

    # Then
    assert header(sent, "x-request-id") == FIXED_ID
    assert log_lines() == [
        {
            "timestamp": "2026-01-02T03:04:05+00:00",
            "service": "canasta-api",
            "env": "preview",
            "request_id": FIXED_ID,
            "method": "GET",
            "path": "/api/x",
            "status_code": 200,
            "latency_ms": 12.3,
            "outcome": "ok",
            "level": "INFO",
            "event": "http_request",
        }
    ]


def test_middleware_does_not_log_query_string_values(
    fixed_clock, fake_timer, fixed_uuid, capsys
):
    # Given
    mw = build(make_app(200), fixed_clock, fake_timer, fixed_uuid)

    # When
    call(mw)

    # Then
    assert "Ana" not in capsys.readouterr().out


def test_middleware_logs_warning_for_client_error(
    fixed_clock, fake_timer, fixed_uuid, log_lines
):
    # Given
    mw = build(make_app(404), fixed_clock, fake_timer, fixed_uuid)

    # When
    call(mw)

    # Then
    (line,) = log_lines()
    assert (line["level"], line["outcome"], line["status_code"]) == (
        "WARNING",
        "client_error",
        404,
    )


def test_middleware_reuses_valid_inbound_request_id(
    fixed_clock, fake_timer, fixed_uuid, log_lines
):
    # Given
    mw = build(make_app(), fixed_clock, fake_timer, fixed_uuid)

    # When
    sent, scope = call(mw, headers=[(b"X-Request-ID", b"abc-123")])

    # Then
    assert header(sent, "X-Request-ID") == "abc-123"
    assert scope["state"]["request_id"] == "abc-123"
    assert log_lines()[0]["request_id"] == "abc-123"


def test_middleware_replaces_invalid_inbound_request_id(
    fixed_clock, fake_timer, fixed_uuid
):
    # Given
    mw = build(make_app(), fixed_clock, fake_timer, fixed_uuid)

    # When
    sent, _ = call(mw, headers=[(b"x-request-id", b"bad id!")])

    # Then
    assert header(sent, "x-request-id") == FIXED_ID


def test_middleware_answers_500_envelope_and_logs_error_on_unhandled_exception(
    fixed_clock, fake_timer, fixed_uuid, log_lines
):
    # Given
    mw = build(
        make_app(raises=RuntimeError("secret-detail")),
        fixed_clock,
        fake_timer,
        fixed_uuid,
    )

    # When
    sent, _ = call(mw)

    # Then
    assert sent[0]["status"] == 500
    assert header(sent, "x-request-id") == FIXED_ID
    body = json.loads(sent[1]["body"])
    assert body["error"]["message"] == "Internal server error"
    assert body["error"]["request_id"] == FIXED_ID
    assert "secret-detail" not in sent[1]["body"].decode()
    (line,) = log_lines()
    assert (line["level"], line["outcome"], line["status_code"]) == (
        "ERROR",
        "server_error",
        500,
    )
    assert line["error_type"] == "RuntimeError"
    assert "secret-detail" not in json.dumps(line)


def test_middleware_reraises_and_still_logs_when_response_already_started(
    fixed_clock, fake_timer, fixed_uuid, log_lines
):
    # Given
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        await send({"type": "http.response.start", "status": 200, "headers": []})
        raise RuntimeError("late")

    mw = build(app, fixed_clock, fake_timer, fixed_uuid)

    # When / Then
    with pytest.raises(RuntimeError, match="late"):
        call(mw)
    (line,) = log_lines()
    assert line["error_type"] == "RuntimeError"
    assert line["status_code"] == 200


def test_middleware_passes_non_http_scopes_through_untouched(
    fixed_clock, fake_timer, fixed_uuid, log_lines
):
    # Given
    seen: list[str] = []

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        seen.append(scope["type"])

    mw = build(app, fixed_clock, fake_timer, fixed_uuid)

    async def receive() -> Message:
        return {"type": "lifespan.startup"}

    async def send(message: Message) -> None:
        raise AssertionError("nothing should be sent")

    # When
    asyncio.run(mw({"type": "lifespan"}, receive, send))

    # Then
    assert seen == ["lifespan"]
    assert log_lines() == []


def test_latency_is_never_negative(fixed_clock, fixed_uuid, log_lines):
    # Given
    ticks = iter([10.0, 9.0])
    mw = build(make_app(), fixed_clock, lambda: next(ticks), fixed_uuid)

    # When
    call(mw)

    # Then
    assert log_lines()[0]["latency_ms"] == 0.0


def test_json_formatter_emits_level_event_and_fields():
    # Given
    record = logging.LogRecord("n", logging.WARNING, "f", 1, "evt", None, None)
    record.event_fields = {"a": 1}

    # When
    parsed = json.loads(JsonFormatter().format(record))

    # Then
    assert parsed == {"a": 1, "level": "WARNING", "event": "evt"}


def test_json_formatter_handles_record_without_fields():
    # Given
    record = logging.LogRecord("n", logging.INFO, "f", 1, "evt", None, None)

    # When
    parsed = json.loads(JsonFormatter().format(record))

    # Then
    assert parsed == {"level": "INFO", "event": "evt"}


def test_configure_logging_is_idempotent():
    # Given
    logger = logging.getLogger("canasta_api.request")

    # When
    configure_logging("INFO")
    configure_logging("ERROR")

    # Then
    assert sum(isinstance(h, StdoutHandler) for h in logger.handlers) == 1
    assert logger.level == logging.ERROR
    configure_logging("INFO")  # Clean


def test_stdout_handler_swallows_write_failures_via_handle_error(
    monkeypatch: pytest.MonkeyPatch,
):
    # Given a stdout that fails on write and a handler that records handleError
    class BrokenStdout:
        def write(self, _: str) -> int:
            raise OSError("closed")

        def flush(self) -> None:
            raise OSError("closed")

    handled: list[logging.LogRecord] = []
    handler = StdoutHandler()
    handler.setFormatter(JsonFormatter())
    monkeypatch.setattr(handler, "handleError", handled.append)
    monkeypatch.setattr("sys.stdout", BrokenStdout())
    record = logging.LogRecord("x", logging.INFO, __file__, 1, "m", None, None)

    # When
    handler.emit(record)

    # Then the failure is routed to handleError, not raised
    assert handled == [record]
