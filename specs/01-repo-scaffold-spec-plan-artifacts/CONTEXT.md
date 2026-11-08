# CONTEXT (state after Iteration 1)

## Current state
- Iteration 1 done: runnable FastAPI app in `apps/api` (health, hello happy path, settings, OpenAPI/docs under `/api`).
- Root hygiene exists: `.gitignore`, `.editorconfig`, placeholder `README.md` (rewritten in iteration 8).
- Not yet present: `errors.py`, `logging.py`, request-ID middleware, error envelope (iteration 2); static hosting, coverage gate (3); `apps/web` (4); e2e + Makefile (5); `api/index.py`, `vercel.json`, `requirements.txt`, integration test (6); CI (7); docs (8).
- 32 tests pass (unit 16, functional 1, interface 15; integration layer empty, default-deselected).
- Versions: Python 3.12.x (uv-managed), fastapi 0.12x+, pydantic-settings, uvicorn; dev: pytest, httpx, ruff, ty.

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
    routers/{health,hello}.py   GET /api/v1/health, /api/v1/hello
    schemas/{health,hello}.py   HealthResponse; HelloResponse, PlayerName, validate_name
    services/hello.py        build_welcome_message(name) (no HTTP imports)
  tests/
    conftest.py              fixtures `settings`, `app`
    unit/   test_settings, test_version, test_services_layering, test_hello_service
    functional/ test_visitor_welcome
    interface/  conftest (`client`), test_health_api, test_hello_api, test_openapi_and_routing
    integration/ conftest only (stub test file comes in iteration 6)
```
Empty `__init__.py` in routers/, schemas/, services/ (tests dirs have none; rootdir-based pytest imports).

## Public interfaces
- `create_app(settings: Settings | None = None) -> FastAPI`. If None, `Settings()` is loaded from env/`.env`. Stores it at `app.state.settings`. Docs `/api/docs`, OpenAPI `/api/openapi.json`, swagger oauth2 redirect `/api/docs/oauth2-redirect`, redoc disabled. `app = create_app()` at module level (needs valid env at import).
- `Settings` fields (attribute / env var): `log_level`/`LOG_LEVEL` (DEBUG|INFO|WARNING|ERROR, default INFO), `app_env`/`APP_ENV` (local|preview|production, default local), `web_dist_dir`/`WEB_DIST_DIR` (Path|None). Fields use `validation_alias` = env name, so validation errors name the env var (e.g. `LOG_LEVEL`). `populate_by_name=True`, `extra="ignore"`, `env_file=".env"`.
- Constants (`Final`, in `canasta_api/settings.py`): `SERVICE_NAME="canasta-api"`, `API_PREFIX="/api"`, `API_V1_PREFIX="/api/v1"`, `DEFAULT_NAME="player"`, `NAME_MIN_LENGTH=1`, `NAME_MAX_LENGTH=40`, `NAME_ALLOWED_PUNCTUATION=frozenset(" '-_")`; types `LogLevel`, `AppEnv`.
- HTTP: `GET /api/v1/health` -> `{"status":"ok","service":"canasta-api","version":__version__}`. `GET /api/v1/hello?name=` -> `{"message":"Welcome to Canasta, <name>!"}`; omitted name = `player`. Invalid name -> 422 (FastAPI default body for now; envelope in iteration 2).
- Name validation (FR-012): `schemas/hello.py::PlayerName = Annotated[str, Query(min_length=1, max_length=40), AfterValidator(validate_name)]`. `validate_name` rejects blank/spaces-only and any char not `isalpha()`, `isdecimal()` or in `NAME_ALLOWED_PUNCTUATION`; returns value unchanged (no trim). The default value (`DEFAULT_PLAYER_NAME`, defined in schemas/hello.py from `DEFAULT_NAME`) is not validated.
- Service: `services/hello.py::build_welcome_message(name: str) -> str`.
- Routers: `routers/health.py::router`, `routers/hello.py::router`, each `APIRouter(prefix=API_V1_PREFIX)`; included by `create_app`.

## Conventions & invariants
- Every route under `/api` (BR-002), domain routes under `/api/v1` (BR-003); test asserts all `Route` paths start with `/api`. Any new FastAPI default route (e.g. oauth2 redirect) must be moved under `/api`.
- `services/` must not import `fastapi`/`starlette` (AST test `tests/unit/test_services_layering.py`).
- `__version__` in `__init__.py` must equal `[project].version` (test `test_version.py`); never use `importlib.metadata` (not installed on Vercel).
- Tests: plain functions, Given/When/Then/Clean comments, module-level `pytestmark = pytest.mark.<layer>`, functional tests carry business docstrings. Default run excludes `integration` via `addopts = "-m 'not integration'"`.
- Settings injection in tests: `Settings(_env_file=None)` (fixture `settings`), `create_app(settings)` (fixture `app`); env cases use `monkeypatch.setenv/delenv`. Interface layer fixture `client` = `TestClient(app)`.
- Ruff rules E,W,F,I,UP,B,SIM, line length 88; `from __future__ import annotations` in all modules.
- ty config: `[tool.ty.environment] python-version = "3.12"`.

## Commands
Run from `apps/api`:
- Install: `uv sync --frozen` (dev: `uv sync`)
- Lint: `uv run ruff check .`; format check: `uv run ruff format --check .`; format: `uv run ruff format .`
- Types: `uv run ty check`
- Tests: `uv run pytest` (excludes integration); per layer `uv run pytest -m unit|functional|interface`
- Serve: `uv run uvicorn canasta_api.main:app --reload` (port 8000)
- Python: `uv run python --version` -> 3.12.x

## Known gaps
- No error envelope, request ID, or wide-event logging yet (iteration 2); `log_level` setting is loaded but unused.
- 422 body is FastAPI's default; 404/405/500 are Starlette defaults.
- No static serving (`web_dist_dir` loaded but unused), no coverage tooling (`pytest-cov`), no integration test file.
- Test run emits a `StarletteDeprecationWarning` (httpx vs `httpx2`); harmless, left as is.
- `uv sync` installs the project itself editable (hatchling); Vercel requirements must use `--no-emit-project` (iteration 6).
- No `tests/**/__init__.py`; test module basenames must stay unique across layers.
