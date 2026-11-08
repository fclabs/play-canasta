# CONTEXT (state after Iteration 7)

## Current state
- Iterations 1-7 done. Iteration 7: GitHub Actions CI (`.github/workflows/ci.yml`, jobs changes/api/web/e2e/ci-ok) and `.github/dependabot.yml`, config test `tests/unit/test_ci_config.py` (PyYAML dev dep). Iteration 6: Vercel config (`vercel.json`), Python function shim `api/index.py`, exported `apps/api/requirements.txt`, config/shim tests, deployed-URL integration tests. Iteration 5: Playwright e2e smoke (4 tests) against uvicorn-served `apps/web/dist`, and root `Makefile`. Web (4): Vite+React+TS welcome page in `apps/web` calling `GET /api/v1/hello`, 20 Vitest tests, 90.7% line coverage (gate 80%), initial JS 67 KB gz. API (1-3): runnable FastAPI app in `apps/api` (health, hello, settings, OpenAPI/docs under `/api`), FR-014 error envelope for every error, `X-Request-ID` on every response, one JSON `http_request` log line per request, optional static web hosting (`WEB_DIST_DIR`), layer-rule meta-test, 90% coverage gate (actual 100%).
- Root hygiene exists: `.gitignore`, `.editorconfig`, placeholder `README.md` (rewritten in iteration 8).
- Not yet present: docs (8). CI has never run on GitHub (no remote verification yet).
- 154 tests pass by default (unit 100, functional 2, interface 52) + 2 integration tests (skipped unless `BASE_URL` set; default-deselected).
- Web versions (installed, locked): node local v26 (engines >=22 <23, only warns), react 19.3, vite 8.3, vitest 5.1, typescript 6.0, eslint 10, prettier 3.9, vitest-axe 0.1, @testing-library/react 16.
- Versions: Python 3.12.x (uv-managed), fastapi 0.12x+, pydantic-settings, uvicorn; dev: pytest, pytest-cov, httpx, ruff, ty, pyyaml (CI config test only; not in requirements.txt).

## File map
```
.gitignore  .editorconfig  README.md (placeholder)  Makefile (install, dev-api, dev-web, test, lint)
vercel.json                  Vercel project config (see Public interfaces)
.github/workflows/ci.yml     CI (see Public interfaces)
.github/dependabot.yml       weekly uv (/apps/api), npm (/apps/web), github-actions (/)
api/index.py                 Vercel function shim: prepends apps/api/src to sys.path, `from canasta_api.main import app`
specs/                       spec, plan, artifacts (this dir)
apps/api/
  requirements.txt           uv export for Vercel (generated; drift-checked in CI)
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
    unit/   conftest (`fixed_clock`, `fake_timer`, `fixed_uuid`), test_settings, test_version, test_services_layering, test_hello_service, test_errors, test_request_logging, test_static, test_layer_rules (meta), test_vercel_config (vercel.json + requirements.txt content), test_ci_config (parses ci.yml + dependabot.yml with PyYAML: permissions, concurrency, timeouts, pinned actions, ci-ok wiring, path filters, weekly ecosystems, no `VERCEL_`)
    functional/ test_visitor_welcome (2 flows)
    interface/  conftest (`client`, `dist_dir`, `static_client`), test_vercel_shim (subprocess loads api/index.py with src off sys.path), test_static_hosting, test_health_latency (NFR-004), test_health_api, test_hello_api, test_openapi_and_routing, test_error_envelope_and_request_id
    integration/ conftest + test_deployed (health 200; `/` HTML contains "Welcome to Canasta"; skipped unless BASE_URL)
apps/web/
  package.json  package-lock.json  .nvmrc (22)  .env.example (VITE_API_BASE_URL=)
  index.html  vite.config.ts (proxy + vitest + coverage)  tsconfig.json  eslint.config.js  .prettierrc  .prettierignore
  playwright.config.ts   e2e/smoke.spec.ts   (@playwright/test, @types/node devDeps)
  scripts/check-bundle-size.mjs   gz initial JS (from dist/index.html refs) <= 150 KB, else exit 1
  src/main.tsx  App.tsx  index.css  vite-env.d.ts  test-setup.ts  vitest-axe.d.ts
  src/api/{client.ts,types.ts,client.test.ts}
  src/pages/{Welcome.tsx,Welcome.test.tsx}   src/App.test.tsx
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

- CI (`.github/workflows/ci.yml`, triggers: `pull_request`, `push` to `main`): top-level `permissions: contents: read`; `concurrency` group `ci-${{ github.workflow }}-${{ github.ref }}`, `cancel-in-progress: true`; every job `timeout-minutes: 15`; actions: `actions/checkout@v4`, `dorny/paths-filter@v3`, `astral-sh/setup-uv@v5`, `actions/setup-python@v5`, `actions/setup-node@v4`. Job ids == names: `changes` (paths-filter; outputs `api`, `web`; `api` filter = `apps/api/**`, `api/**`, `vercel.json`, the workflow file; `web` filter = `apps/web/**` + workflow file), `api` (if changes.api; working-dir apps/api; sync, ruff check, ruff format --check, ty, pytest coverage gate, `uv lock --check`, requirements diff), `web` (if changes.web; Node 22, npm cache; ci, lint, format:check, typecheck, test:coverage, build incl. bundle check), `e2e` (if api or web changed; uv sync --frozen, npm ci, `npx playwright install --with-deps chromium`, `npm run e2e`), `ci-ok` (needs all four, `if: always()`, fails on any `failure`/`cancelled` result in `join(needs.*.result)`, passes on success/skipped). Branch protection must require exactly `ci-ok`. No `VERCEL_` anywhere in workflows (BR-006).
- Web: `getHello(name: string): Promise<HelloResponse>` in `src/api/client.ts` (also exports `ApiError`, `FALLBACK_ERROR_MESSAGE="Could not reach the server"`, `HELLO_PATH`). URL = `${import.meta.env.VITE_API_BASE_URL ?? ""}/api/v1/hello?name=${encodeURIComponent(name)}` (env read at call time, so tests use `vi.stubEnv`). Any failure (network, non-2xx without envelope message, invalid JSON, 200 without string `message`) throws `ApiError`; non-2xx with envelope throws `ApiError(error.message)`.
- Web page accessible contract (reuse in Playwright): heading "Welcome to Canasta" (h1); textbox label "Your name" (`maxlength=40`, id `player-name`); button "Ping API" (type submit in a `<form>`; while pending disabled and named "Pinging…"); success `role="status"` containing the API message; failure `role="alert"`. Result element absent until a request completes. Input value is sliced to 40 on change.
- Web build output: `apps/web/dist` (Vite default); `npm run build` = `tsc --noEmit && vite build && node scripts/check-bundle-size.mjs`.

- Vercel (`vercel.json`, repo root = Vercel Root Directory): `installCommand` `npm ci --prefix apps/web`; `buildCommand` `npm run build --prefix apps/web`; `outputDirectory` `apps/web/dist`; `functions."api/index.py".includeFiles` = `apps/api/src/**`; `rewrites` in order `/api/(.*)` -> `/api/index`, then `/((?!api/).*)` -> `/index.html`; `headers`: `/(.*)` security trio (nosniff, strict-origin-when-cross-origin, DENY), `/assets/(.*)` immutable 1y, `/` and `/index.html` `public, max-age=0, must-revalidate`, `/api/(.*)` `no-store`; `ignoreCommand` = `git diff --quiet HEAD^ HEAD -- . ':!specs' ':!*.md'` (exit 0 = skip build). `WEB_DIST_DIR` must NOT be set on Vercel; set `APP_ENV` = preview/production in Vercel env.
- Shim `api/index.py`: inserts `<repo>/apps/api/src` at `sys.path[0]` (if absent), imports `app`. Project not installed on Vercel (requirements omit it), so version comes from `canasta_api.__version__`.

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
- CI config test: adding a job requires `timeout-minutes: 15` and updating the expected job set in `test_ci_config.py`; actions must use `vN` tags or 40-hex SHAs.
- ty config: `[tool.ty.environment] python-version = "3.12"`.

- Web: no `any` in `src/` outside `*.test.*` (eslint `no-explicit-any` error). Tests are co-located; Vitest globals off (import from `vitest`); `src/test-setup.ts` registers jest-dom + vitest-axe matchers and RTL cleanup. Prettier width 90, double quotes. `tsconfig` strict + noUncheckedIndexedAccess. Only `VITE_*` env referenced. No file in apps/web mentions the api package (BR-001).
- Web script names are exactly: dev, build, preview, lint, format:check, typecheck, test, test:coverage, e2e (no extra scripts; bundle check hangs off `build`). `e2e` = `npm run build && playwright test`.

## Commands
Run from `apps/api`:
- Install: `uv sync --frozen` (dev: `uv sync`)
- Lint: `uv run ruff check .`; format check: `uv run ruff format --check .`; format: `uv run ruff format .`
- Types: `uv run ty check`
- Coverage gate: `uv run pytest --cov=canasta_api --cov-fail-under=90 --cov-report=term-missing` (not in addopts; run explicitly / in CI)
- Integration (needs deployed app): `BASE_URL=https://... uv run pytest -m integration -o addopts=""` (skips without BASE_URL)
- Regenerate Vercel requirements after any dependency change: `uv lock && uv export --no-dev --no-hashes --no-emit-project --frozen > requirements.txt`; verify with `uv lock --check` and `uv export --no-dev --no-hashes --no-emit-project --frozen | diff - requirements.txt`
- Tests: `uv run pytest` (excludes integration); per layer `uv run pytest -m unit|functional|interface`
- Serve: `uv run uvicorn canasta_api.main:app --reload` (port 8000)
- Python: `uv run python --version` -> 3.12.x

Run from `apps/web` (Node 22 per `.nvmrc`): `npm ci`; `npm run dev` (5173, proxy /api -> 127.0.0.1:8000); `npm run lint | format:check | typecheck | test | test:coverage | build | preview`; `npm run e2e`.
- E2E: `cd apps/web && npx playwright install chromium` once (CI: `npx playwright install --with-deps chromium`, as in the `e2e` job), then `npm run e2e`. It builds the bundle (`npm run build`), then Playwright's `webServer` starts `uv run --project ../api uvicorn canasta_api.main:app --host 127.0.0.1 --port 8123` with `WEB_DIST_DIR=<abs apps/web/dist>`, `LOG_LEVEL=WARNING`, waits on `/api/v1/health`, `reuseExistingServer: false`. `playwright.config.ts` throws if `dist/index.html` is missing. Needs `uv` on PATH and `uv sync` done in apps/api. Tests in `e2e/` are excluded from Vitest (`test.exclude`) and included in tsc/eslint. Artifacts `playwright-report/`, `test-results/` are gitignored.
Run from repo root (`Makefile`): `make install` (`uv sync --frozen` + `npm ci`), `make dev-api` (uvicorn --reload on 8000), `make dev-web` (vite 5173, proxies /api to 127.0.0.1:8000), `make test` (api pytest then web vitest; runs both, exits non-zero if either fails), `make lint` (api ruff check, ruff format --check, ty; web lint, format:check, typecheck; both always run). No coverage/e2e targets.

## Known gaps
- `make dev-api` hardcodes port 8000 (the vite proxy target); it fails if another process holds 8000.
- e2e uses port 8123 and Chromium only; Playwright browsers must be installed separately.
- Local Node was v26 while engines pin 22: only an engine warning, never run under real Node 22 locally (CI uses Node 22).
- jsdom prints a harmless "HTMLCanvasElement getContext not implemented" note from axe.
- Bundle check counts `<script src>`/`href` .js refs in dist/index.html only (not dynamic imports; none exist).
- OpenAPI still documents FastAPI's default `HTTPValidationError` for 422 (not the envelope).
- `vercel.json` keys (`functions.includeFiles`, `ignoreCommand`, header `source` patterns for `/`, rewrite destination `/api/index`) are best-known forms, validated only by local content tests; a real deployment is required (spec §10, OQ-1).
- Pending manual (need a real GitHub repo): VC-050 (PRs touching only web / only api / only README / the workflow -> expected jobs run or skip, `ci-ok` green), VC-051 (failing web test and a cancelled api job make `ci-ok` red), VC-075 (branch protection on `main` requires exactly `ci-ok`), VC-074 secrets list empty, NFR-002 CI timing, VC-052 on a real run (modify uv.lock without regenerating requirements.txt). `actionlint` passed locally; workflow never executed on GitHub.
- Pending manual (need a real Vercel project): VC-060, VC-061, VC-062, VC-063 (live curl), VC-064, VC-065, VC-066 (function bundle size, NFR-006), VC-067 NFR-005 (p95 <= 500 ms on preview), VC-054 against a live preview.
- `ignoreCommand` uses `HEAD^`; fails open (builds) on shallow/first commits.
- Static serving sets no cache headers and no index.html `no-cache` policy; Vercel serves assets from the CDN, not this path.
- Test run emits a `StarletteDeprecationWarning` (httpx vs `httpx2`); harmless, left as is.
- `uv sync` installs the project itself editable (hatchling); Vercel requirements must use `--no-emit-project` (iteration 6).
- No `tests/**/__init__.py`; test module basenames must stay unique across layers.
- Meta-test checks error codes by string literal in interface test functions (heuristic, not full semantic proof).
