# Canasta

Play Canasta (you and an AI partner against two AI opponents) in the browser. The
repository is a monorepo with a FastAPI backend (`apps/api`) and a Vite/React/TypeScript
client (`apps/web`). Today it contains the working scaffold only: a welcome page that
calls a dummy API, tests, CI and a Vercel deployment config. No game rules exist yet.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (it installs Python 3.12 for you)
- Node 22 (see `apps/web/.nvmrc`) with npm
- `make` (optional, the commands behind each target are shown in the docs)
- Ports 8000 (API) and 5173 (web dev server) free

## Quick start

```sh
git clone <repository-url> && cd play-canasta
make install
make dev-api    # terminal 1: API on http://127.0.0.1:8000 (docs at /api/docs)
make dev-web    # terminal 2: web on http://localhost:5173
```

Open http://localhost:5173, type a name (for example "Ana") and press "Ping API". You
should see "Welcome to Canasta, Ana!".

## Everyday commands

| Task | Command |
|---|---|
| Run the API (hot reload) | `cd apps/api && uv run uvicorn canasta_api.main:app --reload` |
| Run the web dev server | `cd apps/web && npm run dev` (proxies `/api` to `127.0.0.1:8000`) |
| Tests (API + web) | `make test` |
| Lint, format check, types (API + web) | `make lint` |
| API coverage gate (90%) | `cd apps/api && uv run pytest --cov=canasta_api --cov-fail-under=90` |
| Web coverage gate (80%) | `cd apps/web && npm run test:coverage` |
| Production build (+ bundle size check) | `cd apps/web && npm run build` |
| Browser end-to-end test | `cd apps/web && npx playwright install chromium` (once), then `npm run e2e` |

### Run all gates

Everything CI runs:

```sh
(cd apps/api && uv sync --frozen && uv run ruff check . && uv run ruff format --check . \
  && uv run ty check && uv run pytest --cov=canasta_api --cov-fail-under=90)
(cd apps/web && npm ci && npm run lint && npm run format:check && npm run typecheck \
  && npm run test:coverage && npm run build && npm run e2e)
```

See [docs/getting-started.md](docs/getting-started.md) for details.

## FastAPI serves the built web app (single process)

Instead of two dev servers, the API can serve the built client itself. Build the web app,
then point `WEB_DIST_DIR` at the output:

```sh
cd apps/web && npm run build
cd ../api && WEB_DIST_DIR=../web/dist uv run uvicorn canasta_api.main:app
```

Open http://127.0.0.1:8000. Real files in `dist` are served as-is; any other non-`/api`
`GET` path returns `index.html` (single-page-app fallback); `/api/...` is never shadowed.
When `WEB_DIST_DIR` is unset (or has no `index.html`) the API serves only `/api`. The
end-to-end test uses this mode on port 8123.

## Deploying to Vercel

Import the repository as a Vercel project with:

- **Root Directory**: the repository root (leave it blank/`./`; do not set `apps/web`).
- **Framework preset / build / output / install**: leave them to `vercel.json`, which
  already sets them.
- **Environment variables**: `APP_ENV` = `preview` for the Preview environment and
  `production` for Production. Do not set `WEB_DIST_DIR`: on Vercel the CDN serves the
  static files.
- Deploy through the Vercel Git integration; CI does not deploy and holds no Vercel secrets.

Details, CI setup and troubleshooting: [docs/deployment.md](docs/deployment.md).

## Repository layout

```
apps/api/            FastAPI app (Python 3.12, uv): src/canasta_api, tests, requirements.txt
apps/web/            React client (Vite, TypeScript): src, e2e, scripts
api/index.py         Vercel Python function entrypoint (imports the FastAPI app)
vercel.json          Vercel build, routing and header config
.github/             CI workflow (with the `ci-ok` gate) and Dependabot config
Makefile             install, dev-api, dev-web, test, lint
docs/                documentation
```

## Documentation

- [Overview](docs/overview.md): what exists and why
- [Getting started](docs/getting-started.md): install, run, test, lint, e2e, add an endpoint
- [Architecture](docs/architecture.md): layers, error envelope, logging, API contract, design decisions
- [Deployment](docs/deployment.md): Vercel, CI, branch protection, troubleshooting
- [Limitations](docs/limitations.md): known gaps and gotchas
