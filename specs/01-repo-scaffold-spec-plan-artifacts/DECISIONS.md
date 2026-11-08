# DECISIONS

## D-001: Name validation via AfterValidator, not a regex (Iteration 1)
Context: FR-012 allows `str.isalpha()` letters and `str.isdecimal()` digits; Unicode-aware regex classes (`\w`, Rust regex used by pydantic `pattern`) differ (underscore, `isnumeric` chars such as "²").
Decision: `Query(min_length=1, max_length=40)` plus `AfterValidator(validate_name)` in `schemas/hello.py`, implementing the exact char rules and the not-spaces-only rule; no trimming.
Rejected: `pattern=` regex (not equivalent to isalpha/isdecimal; awkward spaces-only rule).
Consequences: Failures surface as FastAPI 422 with field `name` in `loc`; iteration 2 maps them to the envelope.

## D-002: Settings use uppercase validation aliases; injected through create_app (Iteration 1)
Context: FR-017 requires errors naming the env variable; tests must inject settings rather than use globals.
Decision: fields `log_level`, `app_env`, `web_dist_dir` with `validation_alias="LOG_LEVEL"` etc., so error `loc` shows the env name. `create_app(settings: Settings | None = None)`; tests use `Settings(_env_file=None)` and `monkeypatch.setenv`. No module-level `settings` singleton (only the module-level `app`).
Rejected: lowercase field names with case-insensitive env (errors name `log_level`); global singleton.
Consequences: constructing `Settings` directly by kwarg uses aliases (`LOG_LEVEL=...`) or `populate_by_name`.

## D-003: Swagger OAuth2 redirect moved under /api (Iteration 1)
Context: FastAPI registers `/docs/oauth2-redirect` by default, violating BR-002 (all routes under `/api`).
Decision: `swagger_ui_oauth2_redirect_url="/api/docs/oauth2-redirect"`; ReDoc disabled (`redoc_url=None`).
Rejected: disabling the redirect (changes docs behaviour); leaving it (violates BR-002).
Consequences: route-prefix test passes with no exceptions.

## D-004: Constants live in settings.py; build backend hatchling (Iteration 1)
Context: python-coding skill puts `Final` constants beside settings; project must be a uv-installable package under `src/`.
Decision: all shared `Final` constants (prefixes, service name, name limits) in `canasta_api/settings.py`; `[build-system]` hatchling with wheel package `src/canasta_api`; `uv sync` installs editable.
Rejected: separate constants.py (small now); `package = false` (spec/skill expect src layout package).
Consequences: Vercel export must use `--no-emit-project`; `DEFAULT_PLAYER_NAME` alias defined in schemas/hello.py.

## D-005: Unhandled exceptions handled in the request middleware, not an Exception handler (Iteration 2)
Context: Starlette's `Exception` handler runs in ServerErrorMiddleware, outside user middleware, so the `X-Request-ID` header and the log line would be missed (or the exception re-raised).
Decision: `RequestContextMiddleware` (pure ASGI, outermost user middleware) catches exceptions, sends `errors.internal_error_response`, logs with status 500 and `error_type` (class name only). Re-raises only if the response had already started.
Rejected: `BaseHTTPMiddleware` + Exception handler (header/log gaps, known re-raise behaviour); registering both.
Consequences: no `Exception` handler is registered; TestClient does not raise server exceptions.

## D-006: AppError carries no HTTP status; mapping lives in errors.ERROR_STATUS (Iteration 2)
Context: BR-005 forbids HTTP knowledge in services, yet services raise AppError subclasses.
Decision: `AppError` has `code`/`default_message`/`details` only; `ERROR_STATUS` (handler layer, same module) maps classes to statuses via MRO. Unmapped subclasses answer as generic 500.
Rejected: `status_code` ClassVar on the exception (HTTP leakage); separate errors/handlers modules (plan names a single `errors.py`).
Consequences: `errors.py` imports fastapi, so services importing it are transitively HTTP-aware; AST test covers direct imports only.

## D-007: Logging via stdlib logging with a dynamic-stdout handler (Iteration 2)
Context: FR-016 needs one JSON line on stdout; tests must capture it and mock clock/uuid.
Decision: stdlib `logging` logger `canasta_api.request`, `StdoutHandler` resolving `sys.stdout` at emit time, `JsonFormatter`; clock/timer/uuid injected into the middleware constructor. `service` field added beyond FR-016.
Rejected: structlog (extra dependency); `print`.
Consequences: `LOG_LEVEL` above INFO suppresses `ok` lines (documented in CONTEXT).

## D-008: Static hosting as one catch-all route in `static.py`, not StaticFiles mount (Iteration 3)
Context: FR-018 needs SPA fallback, strict traversal safety, `/api` never shadowed, and non-API 404s on the envelope when unset.
Decision: `static.mount_static` adds a single hidden `GET /{full_path:path}` route after all API routes; `resolve_asset` uses `resolve()` + `is_relative_to` + `is_file`; `/api` paths re-raise a Starlette 404 so the envelope handler answers. Only enabled for a dir with `index.html`.
Rejected: `StaticFiles(html=True)` mount at `/` (no SPA fallback for unknown paths, mount shadows ordering and 404 body is not the envelope); a Starlette 404 exception handler for fallback.
Consequences: with static on, route list contains one non-`/api` route; POST to non-API path gives 405 envelope.

## D-009: Coverage gate is a documented command, not in addopts (Iteration 3)
Context: VC-041 specifies an explicit `pytest --cov ... --cov-fail-under=90` invocation.
Decision: `pytest-cov` added to the dev group; command documented in CONTEXT/README; pyproject `addopts` unchanged so `uv run pytest` stays fast and `--collect-only` per marker unaffected.
Rejected: baking `--cov` into addopts (slows every run, interferes with debugging).
Consequences: CI (iteration 7) must call the full coverage command.

## D-010: Bundle-size check chained into `build`, not a separate script (Iteration 4)
Context: the plan fixes the web scripts to exactly nine names, yet requires a bundle check "invoked by a package script".
Decision: `build` = `tsc --noEmit && vite build && node scripts/check-bundle-size.mjs`; the check gzips JS files referenced by `dist/index.html` and exits 1 above 150 KB.
Rejected: extra `check:bundle` script (violates the exact script list).
Consequences: CI's `npm run build` also enforces VC-066; the script can be run alone after a build.

## D-011: Client throws ApiError with a display-ready message; page only renders it (Iteration 4)
Context: FR-032 needs envelope message when present, else a fixed fallback, for several failure modes.
Decision: `getHello` normalises every failure into `ApiError(message)`; the page shows `error.message` (fallback for non-ApiError). A 200 body without a string `message` also yields the fallback.
Rejected: returning a result union (more branching in UI); exposing raw responses to the page.
Consequences: page stays trivial; coverage and tests focus on the client.
