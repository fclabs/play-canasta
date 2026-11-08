# CONTEXT (state after Iteration 3)

## Current state
- Iterations 1-3 done: runnable FastAPI app in `apps/api` (health, hello, settings, OpenAPI/docs under `/api`), FR-014 error envelope for every error, `X-Request-ID` on every response, one JSON `http_request` log line per request, optional static web hosting (`WEB_DIST_DIR`), layer-rule meta-test, 90% coverage gate (actual 100%).
- Root hygiene exists: `.gitignore`, `.editorconfig`, placeholder `README.md` (rewritten in iteration 8).
- Not yet present: `apps/web` (4); e2e + Makefile (5); `api/index.py`, `vercel.json`, `requirements.txt`, integration test (6); CI (7); docs (8).
- 136 tests pass by default (unit 83, functional 2, interface 51) + 1 integration test (skipped unless `BASE_URL` set; default-deselected).
- Versions: Python 3.12.x (uv-managed), fastapi 0.12x+, pydantic-settings, uvicorn; dev: pytest, pytest-cov, httpx, ruff, ty.

## File map
```
.gitignore  .editorconfig  README.md (placeholder)
specs/                       spec, plan, artifacts (this dir)
apps/api/
  pyproject.toml             project canasta-api 0.1.0; hatchling; ruff/ty/pytest config
  .python-version (3.12)  uv.lock  .env.example
  src/canasta_api/
    __init__.py              __version__ = "0.1.0" (single source)
    settings.py              Settings(BaseSettings) + Final constants
    main.py                  create_app(settings=None) + module-level `app`
    static.py                optional static hosting: is_servable_dist, is_api_path, resolve_asset, mount_static
    errors.py                AppError hierarchy, ERROR_STATUS map, envelope handlers
    logging.py               JsonFormatter, configure_logging, RequestContextMiddleware
    routers/{health,hello}.py   GET /api/v1/health, /api/v1/hello
    schemas/{health,hello,errors}.py   HealthResponse; HelloResponse, PlayerName, validate_name; ErrorEnvelope/ErrorBody
    services/hello.py        build_welcome_message(name) (no HTTP imports)
  tests/
    conftest.py              fixtures `settings`, `app`, `log_lines`
    unit/   conftest (`fixed_clock`, `fake_timer`, `fixed_uuid`), test_settings, test_version, test_services_layering, test_hello_service, test_errors, test_request_logging, test_static, test_layer_rules (meta)
    functional/ test_visitor_welcome (2 flows)
    interface/  conftest (`client`, `dist_dir`, `static_client`), test_static_hosting, test_health_latency (NFR-004), test_health_api, test_hello_api, test_openapi_and_routing, test_error_envelope_and_request_id
    integration/ conftest + test_deployed_health (skipped unless BASE_URL; iteration 6 may extend)
```
Empty `__init__.py` in routers/, schemas/, services/ (tests dirs have none; rootdir-based pytest imports).

## Public interfaces
- `create_app(settings: Settings | None = None) -> FastAPI`. If None, `Settings()` is loaded from env/`.env`. Stores it at `app.state.settings`. Docs `/api/docs`, OpenAPI `/api/openapi.json`, swagger oauth2 redirect `/api/docs/oauth2-redirect`, redoc disabled. `app = create_app()` at module level (needs valid env at import).
- `Settings` fields (attribute / env var): `log_level`/`LOG_LEVEL` (DEBUG|INFO|WARNING|ERROR, default INFO), `app_env`/`APP_ENV` (local|preview|production, default local), `web_dist_dir`/`WEB_DIST_DIR` (Path|None). Fields use `validation_alias` = env name, so validation errors name the env var (e.g. `LOG_LEVEL`). `populate_by_name=True`, `extra="ignore"`, `env_file=".env"`.
- Constants (`Final`, in `canasta_api/settings.py`): `SERVICE_NAME="canasta-api"`, `API_PREFIX="/api"`, `API_V1_PREFIX="/api/v1"`, `DEFAULT_NAME="player"`, `NAME_MIN_LENGTH=1`, `NAME_MAX_LENGTH=40`, `NAME_ALLOWED_PUNCTUATION=frozenset(" '-_")`; types `LogLevel`, `AppEnv`.
- HTTP: `GET /api/v1/health` -> `{"status":"ok","service":"canasta-api","version":__version__}`. `GET /api/v1/hello?name=` -> `{"message":"Welcome to Canasta, <name>!"}`; omitted name = `player`. Invalid name -> 422 `validation_error` envelope.
- Name validation (FR-012): `schemas/hello.py::PlayerName = Annotated[str, Query(min_length=1, max_length=40), AfterValidator(validate_name)]`. `validate_name` rejects blank/spaces-only and any char not `isalpha()`, `isdecimal()` or in `NAME_ALLOWED_PUNCTUATION`; returns value unchanged (no trim). The default value (`DEFAULT_PLAYER_NAME`, defined in schemas/hello.py from `DEFAULT_NAME`) is not validated.
- Service: `services/hello.py::build_welcome_message(name: str) -> str`.
- Static hosting (FR-018): `static.mount_static(app, dist_dir)` adds ONE catch-all `GET /{full_path:path}` (hidden from OpenAPI). `create_app` calls it last, only if `settings.web_dist_dir` is set and `static.is_servable_dist` (dir with `index.html`); otherwise non-API paths hit the normal 404 envelope. `/api` and `/api/...` paths raise a Starlette 404 inside the catch-all (envelope, never HTML). Files are resolved with `resolve_asset(dist, relative)`: `resolve()` + `is_relative_to(root)` + `is_file()`; traversal, symlinks escaping dist, directories, NUL bytes -> None -> `index.html` fallback. Non-GET to a non-API path with static on -> 405 envelope.
- Routers: `routers/health.py::router`, `routers/hello.py::router`, each `APIRouter(prefix=API_V1_PREFIX)`; included by `create_app`.

- Envelope (`schemas/errors.py::ErrorEnvelope` with `ErrorBody`): exactly `{"error": {"code","message","request_id","details"}}`, `details` is `list[dict] | None`. Built by `errors.error_response(status, code, message, request_id, details=None, headers=None)`.
- Error codes: 422 `validation_error` (message "Request validation failed"; details items `{field, location, message, type}`, `field` = loc without its first part, e.g. `name`); 404 `not_found`; 405 `method_not_allowed` (keeps `Allow`); other Starlette HTTP errors `http_error`; 500 `internal_error` message exactly `"Internal server error"`; AppError -> its own `code`.
- `errors.AppError(message=None, *, details=None)`: ClassVars `code` (str) and `default_message`; attrs `message`, `details`. Built-ins `NotFoundError` (code `not_found`, 404) and `ConflictError` (`conflict`, 409). **Add a new error type**: subclass an `AppError` (usually `NotFoundError`/`ConflictError`, which inherit their status via MRO), set `code`/`default_message`, raise it from a service. For a new status, subclass `AppError` and register it in `errors.ERROR_STATUS: dict[type[AppError], int]`. Unregistered AppError subclasses answer as generic 500 `internal_error`. `errors.status_for(exc)` resolves nearest registered base.
- `errors.register_exception_handlers(app)` installs handlers for AppError, RequestValidationError, Starlette HTTPException. There is NO `Exception` handler: unhandled exceptions are caught by the middleware (see below) which sends `errors.internal_error_response(request_id)`.
- Request ID (FR-015): `X-Request-ID` header (constant `REQUEST_ID_HEADER`); inbound kept iff `fullmatch(REQUEST_ID_PATTERN)` else `uuid4`. Stored in `scope["state"]["request_id"]` (read in handlers via `errors.request_id_of(request)`).
- `logging.RequestContextMiddleware(app, *, env, clock=utc_now, timer=perf_counter, uuid_factory=new_uuid)`: pure ASGI; sets request id, adds the response header, logs one line, converts unhandled exceptions to the 500 envelope (re-raises only if the response already started). Log fields: `timestamp` (ISO UTC), `service`, `env`, `request_id`, `method`, `path` (no query), `status_code`, `latency_ms` (>=0, 3 dp), `outcome`, `level` (INFO/WARNING/ERROR), `event`="http_request", plus `error_type` (class name only) on unhandled exceptions.
- `logging.configure_logging(level)` (called by `create_app` with `settings.log_level`): idempotent; attaches `StdoutHandler` (writes to the *current* `sys.stdout`, so capsys works) with `JsonFormatter` to logger `canasta_api.request`, `propagate=False`. Note: `LOG_LEVEL=WARNING|ERROR` suppresses the lower-level request lines.
- Middleware registration order in `create_app`: `configure_logging`, `register_exception_handlers`, then a single `app.add_middleware(RequestContextMiddleware, env=settings.app_env)`. It must stay the outermost user middleware (any middleware added later wraps it; add new ones BEFORE it so it remains outermost).
- New `Final` constants in settings.py: `REQUEST_ID_HEADER`, `REQUEST_ID_PATTERN`, `REQUEST_LOG_EVENT`, `REQUEST_LOGGER_NAME`, `INTERNAL_ERROR_MESSAGE`.

## Conventions & invariants
- Every route under `/api` (BR-002), domain routes under `/api/v1` (BR-003); test asserts all `Route` paths start with `/api` on the default (static-off) app. The only exception is the static catch-all, present only when `WEB_DIST_DIR` is valid. Any new FastAPI default route (e.g. oauth2 redirect) must be moved under `/api`.
- `services/` must not import `fastapi`/`starlette` (AST test `tests/unit/test_services_layering.py`).
- `__version__` in `__init__.py` must equal `[project].version` (test `test_version.py`); never use `importlib.metadata` (not installed on Vercel).
- Static tests: interface fixtures `dist_dir` (tmp `dist/{index.html,assets/app.js}` + `secret.txt` beside it) and `static_client` (`TestClient(create_app(Settings(_env_file=None, WEB_DIST_DIR=dist_dir)))`). Reuse for other tests needing a temp dist.
- Marker conventions: every test module sets `pytestmark = pytest.mark.<unit|functional|interface|integration>` at module level; layers by directory. Meta-test `tests/unit/test_layer_rules.py` (AST) enforces: no `class Test*`; unit tests import no `TestClient` and call no `now/utcnow/today/time/time_ns/perf_counter/monotonic/sleep`; interface tests contain a test mentioning each of `validation_error`, `not_found`, `method_not_allowed`, `internal_error`; functional tests call `create_app()` and have docstrings. Timing tests belong to the interface layer (`test_health_latency.py` uses `time.perf_counter`, allowed there).
- Tests: plain functions, Given/When/Then/Clean comments, module-level `pytestmark = pytest.mark.<layer>`, functional tests carry business docstrings. Default run excludes `integration` via `addopts = "-m 'not integration'"`.
- Settings injection in tests: `Settings(_env_file=None)` (fixture `settings`), `create_app(settings)` (fixture `app`); env cases use `monkeypatch.setenv/delenv`. Interface layer fixture `client` = `TestClient(app)`.
- Ruff rules E,W,F,I,UP,B,SIM, line length 88; `from __future__ import annotations` in all modules.
- Test helpers: root fixture `log_lines` (capsys-based; returns a callable giving the JSON-parsed stdout lines since the last call). Unit conftest: `fixed_clock` (2026-01-02T03:04:05Z), `fake_timer` (12.3 ms per request), `fixed_uuid` (`00000000-0000-4000-8000-000000000000`), injected into `RequestContextMiddleware`. Interface tests add routes to the `app` fixture (`app.add_api_route("/api/v1/_boom", fn)`) and use `TestClient(app, raise_server_exceptions=False)`.
- Services raise `AppError` subclasses only; HTTP statuses live in `errors.ERROR_STATUS` (BR-005). `errors.py` imports fastapi, so services importing it is transitively HTTP-aware but passes the AST test (direct imports only).
- Every non-2xx response must use the envelope; tests assert it via the `assert_envelope` helper in `tests/interface/test_error_envelope_and_request_id.py`.
- ty config: `[tool.ty.environment] python-version = "3.12"`.

## Commands
Run from `apps/api`:
- Install: `uv sync --frozen` (dev: `uv sync`)
- Lint: `uv run ruff check .`; format check: `uv run ruff format --check .`; format: `uv run ruff format .`
- Types: `uv run ty check`
- Coverage gate: `uv run pytest --cov=canasta_api --cov-fail-under=90 --cov-report=term-missing` (not in addopts; run explicitly / in CI)
- Integration (needs deployed app): `BASE_URL=https://... uv run pytest -m integration -o addopts=""`
- Tests: `uv run pytest` (excludes integration); per layer `uv run pytest -m unit|functional|interface`
- Serve: `uv run uvicorn canasta_api.main:app --reload` (port 8000)
- Python: `uv run python --version` -> 3.12.x

## Known gaps
- OpenAPI still documents FastAPI's default `HTTPValidationError` for 422 (not the envelope).
- Integration test is only a health-check stub (extend in iteration 6).
- Static serving sets no cache headers and no index.html `no-cache` policy; Vercel serves assets from the CDN, not this path.
- Test run emits a `StarletteDeprecationWarning` (httpx vs `httpx2`); harmless, left as is.
- `uv sync` installs the project itself editable (hatchling); Vercel requirements must use `--no-emit-project` (iteration 6).
- No `tests/**/__init__.py`; test module basenames must stay unique across layers.
- Meta-test checks error codes by string literal in interface test functions (heuristic, not full semantic proof).
