# Getting started

Task-oriented recipes. Run commands from the repository root unless a `cd` says otherwise.

## Prerequisites

- uv (installs and manages Python 3.12; the version is pinned in `apps/api/.python-version`)
- Node 22 and npm (`apps/web/.nvmrc`; `package.json` declares `>=22 <23`, other majors
  only print an engine warning)
- `make` (optional; every target is a thin wrapper shown below)

## Install

```sh
make install
```

This runs `uv sync --frozen` in `apps/api` and `npm ci` in `apps/web`. Both use the
committed lockfiles, so a clean install leaves `git status` clean. The two parts install
independently: either works without the other.

For local configuration copy `apps/api/.env.example` to `apps/api/.env` (optional; the
defaults work) and `apps/web/.env.example` to `apps/web/.env`. `.env` files are never
committed.

## Run

Two dev servers, in two terminals:

```sh
make dev-api    # cd apps/api && uv run uvicorn canasta_api.main:app --reload
make dev-web    # cd apps/web && npm run dev
```

- API: http://127.0.0.1:8000, interactive docs at http://127.0.0.1:8000/api/docs
- Web: http://localhost:5173; the Vite dev server proxies `/api` to `127.0.0.1:8000`, so
  the browser sees one origin.

Quick checks:

```sh
curl http://127.0.0.1:8000/api/v1/health
curl "http://127.0.0.1:8000/api/v1/hello?name=Ana"    # {"message":"Welcome to Canasta, Ana!"}
```

The proxy target and `make dev-api` both assume port 8000. If something else holds
that port, see [limitations](limitations.md).

### Single process (API serves the web build)

```sh
cd apps/web && npm run build
cd ../api && WEB_DIST_DIR=../web/dist uv run uvicorn canasta_api.main:app --port 8001
```

Open http://127.0.0.1:8001. See [architecture](architecture.md#static-hosting) for the rules.

### Settings

| Variable | Values | Default | Purpose |
|---|---|---|---|
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | `INFO` | Request log level. Above `INFO` hides the one-line-per-request logs of successful calls. |
| `APP_ENV` | `local`, `preview`, `production` | `local` | Reported as `env` in log lines. |
| `WEB_DIST_DIR` | path | unset | Enables static hosting of a built web bundle. |
| `VITE_API_BASE_URL` (web) | URL | empty | API origin for the client; empty means same origin. |

An invalid value stops startup with an error that names the variable.

## Test

```sh
make test                      # API pytest, then web Vitest; runs both, fails if either fails
cd apps/api && uv run pytest   # API only (integration tests excluded)
cd apps/web && npm test        # web only
```

API tests are grouped by marker/directory: `uv run pytest -m unit`, `-m functional`,
`-m interface`. Coverage gates:

```sh
cd apps/api && uv run pytest --cov=canasta_api --cov-fail-under=90 --cov-report=term-missing
cd apps/web && npm run test:coverage      # fails below 80% line coverage
```

Integration tests check a deployed URL and skip unless `BASE_URL` is set:

```sh
cd apps/api && BASE_URL=https://your-preview.vercel.app uv run pytest -m integration -o addopts=""
```

## Lint, format, types

```sh
make lint
```

Equivalent to, in `apps/api`: `uv run ruff check .`, `uv run ruff format --check .`,
`uv run ty check`; in `apps/web`: `npm run lint`, `npm run format:check`,
`npm run typecheck`. To fix formatting: `uv run ruff format .` (api) and
`npx prettier --write .` (web).

## Build the web app

```sh
cd apps/web && npm run build
```

Type-checks, builds to `apps/web/dist`, and fails if the gzipped initial JavaScript
exceeds 150 KB.

## End-to-end test

```sh
cd apps/web
npx playwright install chromium    # once per machine
npm run e2e
```

`npm run e2e` builds the web bundle, starts the API with `WEB_DIST_DIR` on port 8123,
and runs the Playwright smoke tests in Chromium (welcome flow, error state, 375 px and
1280 px layouts). It needs `uv sync` to have been run in `apps/api`.

## Regenerate `requirements.txt`

Vercel installs `apps/api/requirements.txt`, which is exported from the lockfile. After
any change to API dependencies:

```sh
cd apps/api
uv lock
uv export --no-dev --no-hashes --no-emit-project --frozen > requirements.txt
```

Verify (CI runs the same checks):

```sh
uv lock --check
uv export --no-dev --no-hashes --no-emit-project --frozen | diff - requirements.txt
```

## Add an endpoint

Example: `GET /api/v1/goodbye?name=`. Follow the layers (see
[architecture](architecture.md#layers)).

1. **Service** (`apps/api/src/canasta_api/services/hello.py`, or a new module): plain
   Python, no FastAPI/Starlette imports.

   ```python
   def build_farewell_message(name: str) -> str:
       """Return the farewell message for an already validated player name."""
       return f"See you at the table, {name}!"
   ```

2. **Schema** (`schemas/`): request/response models. The example reuses `HelloResponse`
   and the validated `PlayerName` type.
3. **Router** (`routers/goodbye.py`): the prefix must be `API_V1_PREFIX`.

   ```python
   router = APIRouter(prefix=API_V1_PREFIX, tags=["goodbye"])

   @router.get("/goodbye")
   def get_goodbye(name: PlayerName = DEFAULT_PLAYER_NAME) -> HelloResponse:
       return HelloResponse(message=build_farewell_message(name))
   ```

4. **Register** it in `create_app` (`main.py`): `from canasta_api.routers import goodbye`
   and `app.include_router(goodbye.router)` next to the other routers (before the static
   hosting step, which must stay last).
5. **Tests**: add a unit test for the service (`tests/unit`) and an interface test using
   the `client` fixture (`tests/interface`). Every test module sets
   `pytestmark = pytest.mark.<layer>` and test files must have unique names across
   layers. Use plain functions with Given/When/Then comments.
6. **Errors**: raise an `AppError` subclass from the service rather than an HTTP error;
   see [architecture](architecture.md#error-envelope) for how to map it to a status.
7. Run `make lint`, `make test` and the API coverage gate.

To call it from the web client, add a function next to `getHello` in
`apps/web/src/api/client.ts` and a test beside it. Only `/api/...` paths are proxied and
routed to the API in every environment.
