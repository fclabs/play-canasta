# Iteration 2: Error envelope, request ID, wide-event logging

Commit: see `git log`; message `feat(api): error envelope, request IDs and wide-event request logging`.

## Criteria (run from /Users/fede/devel/fclabs/play-canasta/apps/api)
| Criterion | Command / check | Result |
|---|---|---|
| VC-012 (envelope) | `tests/interface/test_hello_api.py::test_hello_rejects_invalid_names_with_422` (5 cases: empty, 41 chars, `<script>`, spaces, `a;b`; asserts `validation_error`, message, details field `name`, request_id); 1/40 chars -> 200 in `test_hello_accepts_valid_names`; unit `test_errors.py::test_handle_validation_error_lists_offending_fields` | PASS |
| VC-013 | `test_error_envelope_and_request_id.py::test_unknown_api_path_returns_404_not_found_envelope` (+ `/api/nope`) | PASS |
| VC-014 | same file: `test_post_to_health_returns_405_...`, `test_unhandled_exception_returns_generic_500_without_leaking` | PASS |
| VC-015 | same file: inbound valid echoed, `bad id!`/65 chars -> uuid4, missing -> uuid4; unit `test_resolve_request_id_*` | PASS |
| VC-016 | same file: `test_one_wide_event_line_per_request` (200/404/500), `test_log_line_never_contains_query_values`, `test_log_env_reflects_app_env`; unit `test_request_logging.py` | PASS |
| VC-073 (both halves) | `tests/unit/test_services_layering.py` (AST) + `test_app_error_from_service_maps_to_http_status` | PASS |
| Gates | `rm -rf .venv && uv sync --frozen`; `uv run ruff check .`; `uv run ruff format --check .`; `uv run ty check`; `uv run pytest` (91 passed) all exit 0 | PASS |
| Artifacts | CONTEXT.md, DECISIONS.md (D-005..D-007), this record | PASS |

## Files
Added: `src/canasta_api/{errors,logging}.py`, `src/canasta_api/schemas/errors.py`, `tests/unit/test_errors.py`, `tests/unit/test_request_logging.py`, `tests/interface/test_error_envelope_and_request_id.py`, this record.
Changed: `main.py` (logging config, handlers, middleware), `settings.py` (new Finals), `tests/conftest.py` (`log_lines`), `tests/unit/conftest.py` (clock/timer/uuid fixtures), `tests/interface/test_hello_api.py` (envelope asserts), `tests/functional/test_visitor_welcome.py` (second flow), CONTEXT.md, DECISIONS.md.
Deleted: none.

## Deviations
- No `Exception` handler registered; middleware produces the 500 envelope (D-005). Plan wording "handlers for unhandled exceptions" is met via `errors.internal_error_response`.
- Extra log fields `service` and (on exceptions) `error_type`; allowed by "at least".

## Gotchas
- pytest adds handlers to every logger; count only `StdoutHandler` when asserting idempotence.
- `StdoutHandler` must resolve `sys.stdout` at emit time or capsys sees nothing.
- `canasta_api/logging.py` shadows nothing (absolute imports), but never run modules as scripts from inside the package dir.
- `LOG_LEVEL` > INFO hides `ok` request lines.
- Starlette `HTTPException` handler covers FastAPI's (subclass); 405 keeps the `Allow` header.

## For the next iteration
- Static hosting must keep `/api/*` 404s as the envelope and non-API 404s when unset (the handler already covers any Starlette 404; if you mount static routes, keep them out of `/api`).
- Meta-test VC-040b: interface tests per error code exist (404, 405, 422, 500 in `test_error_envelope_and_request_id.py`); unit tests use no TestClient and mock the clock via `fixed_clock`.
- Any new middleware must be added before `RequestContextMiddleware` in `create_app` so it stays outermost.
- Coverage: errors.py/logging.py unit-covered; `handle_http_error` ValueError branch is `pragma: no cover`.
