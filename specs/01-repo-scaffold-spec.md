# Spec 01 — Repository Scaffold, CI, Testing and Vercel Deployment

- **Version:** 0.2
- **Status:** Reviewed (round 1 findings applied)
- **Last Updated:** 2026-11-08
- **Owner:** Federico Castañeda
- **Series:** Spec 01 of the Canasta project. Requirement IDs in later specs use distinct ranges (02 → 2xx, 03 → 3xx, …) and cite this spec's IDs when re-stating them.

## 1. Purpose

Canasta (4 players: the human + 1 AI partner vs. 2 AI opponents) will be built as a Python/FastAPI backend and a TypeScript/React web client, with the AI decision logic kept separate from the game engine. Before any game logic exists, the project needs a repository whose two parts (`api`, `web`) build, test, lint and deploy independently, a CI pipeline that gates merges on each part, and a working end-to-end slice — a welcome page that calls a dummy API — deployed to Vercel. This spec defines that scaffold so later specs (game rules and scoring, AI-engine interface, decision/game logging) can be added without restructuring.

## 2. Scope

### In

- Monorepo layout with `apps/api` (Python) and `apps/web` (TypeScript), each with its own toolchain, lockfile, lint, type-check and test setup.
- Dummy API (`/api/v1/health`, `/api/v1/hello`), standard error envelope, request-ID propagation, structured JSON wide-event request logging, env-backed settings.
- Welcome page that queries the dummy API and shows loading / success / error states.
- Test suites for both parts, including the layered pytest layout (unit / functional / interface / integration) and a browser end-to-end smoke test.
- GitHub Actions CI with path-aware jobs per part, an end-to-end job, and a single aggregate required check.
- Vercel deployment config: static web on the CDN, FastAPI as a Python function behind `/api/*`, security headers, cache headers.
- FastAPI optionally serving the built web bundle (local / single-process mode).
- README with the commands needed to install, run, test and deploy.

### Out

- Any Canasta rules, cards, deck, melds, scoring, turn handling, or game state (Spec 02+).
- AI-engine interface and implementations (random or otherwise) (Spec 03+).
- Game/decision log schema and offline-analysis tooling (Spec 04+). The scaffold's request logging is *not* the game log.
- Authentication, user accounts, persistence/database, WebSockets or any real-time transport.
- CORS: the API is same-origin only (served via the Vite proxy, FastAPI static mode, or Vercel rewrites); no CORS middleware is added.
- Custom domain, Vercel Analytics, monitoring/alerting, i18n, PWA/offline support.
- Deploying via GitHub Actions (deployment is done by the Vercel Git integration; see BR-006).

## 3. Actors

| Actor | Description | Permissions |
|-------|-------------|-------------|
| Developer | Contributor working locally | Read/write repo, run all commands, open PRs |
| CI | GitHub Actions runner | Read repo, run lint/type/test/build; no deploy credentials |
| Vercel | Git-integrated build/deploy platform | Build on every push; preview deployment per PR branch; production deployment from `main` |
| Visitor | Person opening the deployed site | Load the welcome page, call public `/api/*` endpoints; no auth |

## 4. Repository Layout (normative)

```
play-canasta/
├── apps/
│   ├── api/
│   │   ├── pyproject.toml            # requires-python = ">=3.12,<3.13"; ruff, ty, pytest config
│   │   ├── .python-version           # 3.12
│   │   ├── uv.lock
│   │   ├── requirements.txt          # generated: uv export --no-dev --no-hashes --no-emit-project (used by Vercel)
│   │   ├── .env.example
│   │   ├── src/canasta_api/
│   │   │   ├── __init__.py               # defines __version__ (single source of the API version)
│   │   │   ├── main.py               # create_app() factory + module-level `app`
│   │   │   ├── settings.py           # Settings(BaseSettings) + Final constants
│   │   │   ├── errors.py             # AppError hierarchy + exception handlers
│   │   │   ├── logging.py            # JSON wide-event logging + request middleware
│   │   │   ├── routers/{health.py,hello.py}
│   │   │   ├── schemas/{health.py,hello.py,errors.py}
│   │   │   └── services/hello.py     # business logic, no HTTP imports
│   │   └── tests/{conftest.py,unit/,functional/,interface/,integration/}
│   └── web/
│       ├── package.json              # "engines": {"node": ">=22 <23"}; scripts below
│       ├── package-lock.json
│       ├── .nvmrc                    # 22
│       ├── .env.example
│       ├── index.html
│       ├── vite.config.ts            # dev proxy /api → http://127.0.0.1:8000
│       ├── tsconfig.json             # "strict": true
│       ├── eslint.config.js, .prettierrc
│       ├── src/{main.tsx,App.tsx,pages/Welcome.tsx,api/client.ts,api/types.ts}
│       ├── src/**/*.test.tsx         # co-located Vitest tests
│       └── e2e/                      # Playwright smoke test
├── api/index.py                      # Vercel entrypoint shim: prepends apps/api/src to sys.path, then `from canasta_api.main import app`
├── vercel.json
├── .github/
│   ├── workflows/ci.yml
│   └── dependabot.yml
├── Makefile                          # thin wrappers: install, dev-api, dev-web, test, lint
├── .gitignore, .editorconfig, README.md
└── specs/                            # spec documents (this file)
```

Reserved for later specs (not created now): `canasta_api/{game,engine,ai,gamelog}/`. The scaffold must not add empty placeholder packages for them.

`apps/web` scripts (exact names): `dev`, `build`, `preview`, `lint`, `format:check`, `typecheck`, `test`, `test:coverage`, `e2e`.

## 5. Functional Requirements

### Repository and tooling

**FR-001 (Must) — Independent parts.**
Given a fresh clone, When a developer runs `uv sync` in `apps/api` and `npm ci` in `apps/web`, Then each part installs without requiring the other to be installed and without touching files outside its own directory (except `.venv/` and `node_modules/` inside that directory).

**FR-002 (Must) — Pinned toolchains.**
Given the repository, When toolchain versions are inspected, Then Python is pinned to 3.12 (`.python-version`, `requires-python`), Node to 22 (`.nvmrc`, `engines`), and both lockfiles (`uv.lock`, `package-lock.json`) are committed.

**FR-003 (Must) — Quality gates available locally.**
Given a configured part, When the developer runs its gate commands, Then they exist and run: for api — `uv run ruff check .`, `uv run ruff format --check .`, `uv run ty check`, `uv run pytest`; for web — `npm run lint`, `npm run format:check`, `npm run typecheck`, `npm test`.

**FR-004 (Should) — Root convenience.**
Given the root `Makefile`, When `make install`, `make test`, `make lint`, `make dev-api` or `make dev-web` is run, Then it delegates to the per-part commands in FR-003 and the dev servers described in FR-011.

### API

**FR-010 (Must) — Health endpoint.**
Given the API is running, When a client sends `GET /api/v1/health`, Then it responds `200` with JSON `{"status": "ok", "service": "canasta-api", "version": "<API_VERSION>"}` where `API_VERSION` is `canasta_api.__version__`; a unit test asserts it equals `[project].version` in `pyproject.toml` (the package is not installed on Vercel, so `importlib.metadata` must not be used) and `Content-Type: application/json`.

**FR-011 (Must) — Hello endpoint, happy path.**
Given the API is running, When a client sends `GET /api/v1/hello?name=Ana`, Then it responds `200` with JSON `{"message": "Welcome to Canasta, Ana!"}`; when `name` is omitted, `name` defaults to `player`.

**FR-012 (Must) — Hello input validation.**
Given the API is running, When `name` is empty, longer than 40 characters, consists only of spaces, or contains a character that is not a letter (`str.isalpha()`), digit (`str.isdecimal()`), space, apostrophe, hyphen or underscore, Then it responds `422` with the error envelope of FR-014 and `error.code == "validation_error"`, a non-empty human-readable `message`, and `details` listing the offending field. `name` is not trimmed or otherwise normalised.

**FR-013 (Must) — Unknown routes.**
Given the API is running, When a client requests a path under `/api/` that is not defined, Then it responds `404` with the error envelope and `error.code == "not_found"`.

**FR-014 (Must) — Error envelope.**
Given any non-2xx response produced by the API (validation, not found, method not allowed → `405`/`method_not_allowed`, unhandled exception → `500`/`internal_error`), Then the body is exactly `{"error": {"code": str, "message": str, "request_id": str, "details": list | null}}`; for `500` the `message` is the generic text `"Internal server error"` and contains no stack trace, exception text or file paths.

**FR-015 (Must) — Request ID.**
Given any request to the API, When it is handled, Then the response carries an `X-Request-ID` header: the inbound `X-Request-ID` value if it matches `^[A-Za-z0-9._-]{1,64}$`, otherwise a newly generated UUID4.

**FR-016 (Must) — Wide-event request logging.**
Given any request to the API, When the response is sent, Then exactly one JSON log line is written to stdout containing at least: `timestamp` (ISO-8601 UTC), `level`, `event` (`"http_request"`), `env` (the `APP_ENV` value), `request_id`, `method`, `path`, `status_code`, `latency_ms` (number ≥ 0), `outcome` (`"ok"` for status < 400, `"client_error"` for 4xx, `"server_error"` for 5xx); `level` is `INFO` for `ok`, `WARNING` for `client_error`, `ERROR` for `server_error`. The line is emitted even when the handler raised an unhandled exception. Query-string values are not logged.

**FR-017 (Must) — Settings.**
Given the environment, When the app starts, Then `Settings` (pydantic-settings) loads: `LOG_LEVEL` (default `INFO`; one of DEBUG/INFO/WARNING/ERROR), `WEB_DIST_DIR` (optional path, default unset), `APP_ENV` (default `local`; one of local/preview/production). An invalid value makes startup fail with a validation error naming the variable.

**FR-018 (Should) — Static web hosting by FastAPI.**
Given `WEB_DIST_DIR` points to an existing directory containing `index.html`, When a client requests `GET /` or any non-`/api/` path that does not match a file, Then the API returns `index.html` (`200`, SPA fallback); a path matching a file returns that file; paths that resolve outside `WEB_DIST_DIR` (e.g. `/../x`, encoded `%2e%2e`) never return files from outside it (they return `index.html` or `404`, never the outside file). When `WEB_DIST_DIR` is unset, non-`/api/` paths return `404` with the error envelope. `/api/*` routing is never shadowed by static serving.

**FR-019 (Must) — OpenAPI.**
Given the API is running, When a client requests `GET /api/openapi.json`, Then it responds `200` with a valid OpenAPI 3 document listing `/api/v1/health` and `/api/v1/hello`; interactive docs are served at `/api/docs`.

### Web

**FR-030 (Must) — Welcome page.**
Given a visitor opens `/`, When the page loads, Then it shows a heading "Welcome to Canasta", a one-sentence description of the game, a text input labelled "Your name" (max length 40), and a button "Ping API"; no network request is made until the button is pressed.

**FR-031 (Must) — API query, success.**
Given the welcome page, When the visitor types a name and presses "Ping API" and the API returns `200`, Then the page shows the returned `message` text in an element with `role="status"`; while the request is pending the button is disabled and shows "Pinging…".

**FR-032 (Must) — API query, failure.**
Given the welcome page, When the request fails — API returns a non-2xx response with the FR-014 envelope, the response is not valid JSON, or the network is unreachable — Then the page shows, in an element with `role="alert"`, the envelope's `error.message` when present and otherwise the text "Could not reach the server", and the button re-enables.

**FR-033 (Must) — Client-side input check.**
Given the welcome page, When the name input is longer than 40 characters (pasted), Then the value is truncated to 40 characters and no request carries more than 40 characters.

**FR-034 (Must) — API base configuration.**
Given the web client, When it builds a request URL, Then it uses `VITE_API_BASE_URL` (default empty string, i.e. same origin) joined with `/api/v1/hello`. A non-empty `VITE_API_BASE_URL` must point to a same-origin or CORS-enabled host (no CORS is provided by this spec). In `npm run dev`, requests to `/api/*` are proxied to `http://127.0.0.1:8000`.

**FR-035 (Should) — Accessibility baseline.**
Given the welcome page, When audited with axe (via `vitest-axe` or Playwright axe), Then there are zero violations of impact "serious" or "critical", and the page is fully operable by keyboard.

### Testing

**FR-040 (Must) — API test layers.**
Given `apps/api/tests`, Then the directories `unit/`, `functional/`, `interface/`, `integration/` exist, each with a `conftest.py`, markers `unit`, `functional`, `interface`, `integration` are registered, tests are plain functions following Given/When/Then/Clean, and `uv run pytest` runs everything except `integration` by default.

**FR-045 (Must) — API test layer rules.**
Given the API test layers, Then: unit tests mock all external I/O (clock, uuid, stdout sink) and cover every failure branch; interface tests use FastAPI `TestClient` as a black box and cover the happy path plus every documented error response of FR-010…FR-019; functional tests carry business-language docstrings and cover the "visitor is welcomed" flow through the real app; the integration test targets the deployed URL in `BASE_URL` and is skipped when unset.

**FR-041 (Must) — API coverage gate.**
Given `uv run pytest --cov=canasta_api --cov-fail-under=90`, When run, Then it passes; every reachable failure branch in `src/` is covered by a unit test.

**FR-042 (Must) — Web unit/component tests.**
Given `npm test`, When run, Then Vitest + Testing Library (jsdom) executes component tests for the welcome page covering FR-030…FR-033 and unit tests for `api/client.ts` covering success, non-2xx envelope, invalid JSON and network failure, using a mocked `fetch` (or MSW); no real network access occurs.

**FR-043 (Must) — Web coverage gate.**
Given `npm run test:coverage`, When run, Then line coverage of `src/` is ≥ 80% and the command exits non-zero below that threshold.

**FR-044 (Should) — End-to-end smoke.**
Given the built web bundle served by the real FastAPI app via `WEB_DIST_DIR`, When Playwright (Chromium) opens `/`, types "Ana", presses "Ping API", Then `role="status"` shows "Welcome to Canasta, Ana!"; and when the Playwright test aborts the `/api/**` request (`page.route(...).abort()`), the page shows the `role="alert"` failure message.

### CI

**FR-050 (Must) — CI workflow.**
Given a pull request or a push to `main`, When GitHub Actions runs `.github/workflows/ci.yml`, Then it executes: a `changes` job (path filter: `apps/api/**`, `api/**`, `vercel.json` → api; `apps/web/**` → web; workflow file change → both), an `api` job (FR-003 api gates + coverage gate, Python 3.12, uv cache), a `web` job (FR-003 web gates + coverage gate + `npm run build`, Node 22, npm cache), an `e2e` job (FR-044, runs when either part changed), and a final `ci-ok` job.

**FR-051 (Must) — Aggregate required check.**
Given the `ci-ok` job with `needs: [changes, api, web, e2e]` and `if: always()`, When any needed job failed or was cancelled, Then `ci-ok` fails; when needed jobs succeeded or were skipped by the path filter, Then `ci-ok` passes. `ci-ok` is the only check configured as required by branch protection on `main`.

**FR-052 (Must) — Lockfile / export drift.**
Given the `api` job, When `apps/api/requirements.txt` differs from the output of `uv export --no-dev --no-hashes --no-emit-project --frozen` or `uv.lock` is out of date (`uv lock --check`), Then the job fails.

**FR-053 (Should) — CI hygiene.**
Given the workflow, Then it declares `permissions: contents: read`, cancels superseded runs per ref (`concurrency` with `cancel-in-progress: true`), sets `timeout-minutes: 15` on each job, pins third-party actions to a major version or SHA, and Dependabot (`.github/dependabot.yml`) opens weekly update PRs for `uv` (apps/api), `npm` (apps/web) and `github-actions`.

**FR-054 (Could) — Post-deploy smoke.**
Given a Vercel preview deployment succeeded, When the `integration` pytest layer runs with `BASE_URL` set to the preview URL, Then it verifies `GET /api/v1/health` returns `200` and `GET /` returns HTML containing "Welcome to Canasta".

### Vercel deployment

**FR-060 (Must) — Single Vercel project.**
Given the repository imported as one Vercel project with Root Directory = repository root, When Vercel builds, Then it runs `npm ci --prefix apps/web` and `npm run build --prefix apps/web`, publishes `apps/web/dist` as the static output, and builds `api/index.py` as a Python function using `apps/api/requirements.txt` for dependencies.

**FR-061 (Must) — Routing.**
Given `vercel.json`, Then its `rewrites` are, in this order: `{"source": "/api/(.*)", "destination": "/api/index"}` (all API traffic goes to the FastAPI function, which sees the original `/api/...` path because the app serves under the `/api` prefix) and `{"source": "/((?!api/).*)", "destination": "/index.html"}` (SPA fallback for paths that don't match a static file); `/api/*` is never rewritten to `index.html`.

**FR-062 (Must) — Function entrypoint.**
Given `api/index.py`, Then it exposes the ASGI object as `app` by importing `canasta_api.main:app`, and `api/index.py` prepends `apps/api/src` to `sys.path`, and the function bundle includes `apps/api/src` (via `vercel.json` `functions.includeFiles` or an equivalent supported mechanism) so the import succeeds on Vercel. `WEB_DIST_DIR` is not set on Vercel (static assets are served by the CDN, not the function).

**FR-063 (Must) — Headers.**
Given a deployed response (headers configured through `vercel.json` `headers`), Then it carries `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `X-Frame-Options: DENY`; files under `/assets/` carry `Cache-Control: public, max-age=31536000, immutable`; `index.html` carries `Cache-Control: public, max-age=0, must-revalidate`; `/api/*` responses carry `Cache-Control: no-store`.

**FR-064 (Must) — Environments.**
Given Vercel Git integration, Then every pull request branch gets a preview deployment, `main` deploys to production, `APP_ENV` is `preview` or `production` accordingly (set in Vercel project env), and no secrets are required for this spec.

**FR-065 (Should) — Ignored builds.**
Given a commit that only changes `specs/**` or `*.md`, When Vercel evaluates `ignoreCommand` in `vercel.json`, Then the build is skipped.

### Documentation

**FR-070 (Must) — README.**
Given `README.md`, Then it documents: prerequisites (uv, Node 22), install, run API (`uv run uvicorn canasta_api.main:app --reload` from `apps/api`), run web (`npm run dev`), run all gates, how FastAPI-serves-static mode works, the Vercel project settings required (FR-060), and the repository layout.

## 6. Business Rules

- **BR-001 — Decoupled parts.** `apps/web` and `apps/api` share no source code; their only contract is HTTP JSON under `/api/v1/`. *Rationale:* allows independent CI, deploy and, later, swapping AI/engine internals without touching the client. *Exceptions:* none.
- **BR-002 — `/api` prefix.** Every backend route (including docs and OpenAPI) lives under `/api/`. *Rationale:* a single Vercel rewrite rule and unambiguous static/API separation. *Exceptions:* none.
- **BR-003 — Versioned API.** Domain endpoints live under `/api/v1/`; a breaking change to a response shape requires a new version prefix. `/api/docs` and `/api/openapi.json` are unversioned.
- **BR-004 — No secrets in git.** `.env` files are git-ignored; only `.env.example` with placeholders is committed. Browser-exposed `VITE_*` variables must never hold secrets.
- **BR-005 — Layering.** In the API, `services/` contains no FastAPI/HTTP imports; domain exceptions (subclasses of `AppError`) are mapped to HTTP statuses only in the router/handler layer. *Rationale:* the future game engine and AI code must be callable without HTTP.
- **BR-006 — Deploy via Vercel Git integration.** CI never holds Vercel tokens; Actions only validates. *Rationale:* least privilege; previews come for free. *Exceptions:* none for this spec.
- **BR-007 — Merge gate.** A PR may merge into `main` only when `ci-ok` is green. *Rationale:* a single stable required-check name survives path filtering and job renames.
- **BR-008 — Type safety.** API code is fully annotated and passes `ty check` with no errors; web code compiles under `"strict": true` with no `any` in `src/` except in test files.

## 7. Non-Functional Requirements

| ID | Requirement | Threshold |
|----|-------------|-----------|
| NFR-001 | Time from clean clone to both dev servers running | ≤ 5 documented shell commands, no manual file editing |
| NFR-002 | CI wall-clock time on a warm cache (all jobs running) | ≤ 8 minutes; `api` job ≤ 3 min, `web` job ≤ 4 min |
| NFR-003 | Initial JS payload of the web bundle | ≤ 150 KB gzipped (measured on `vite build` output) |
| NFR-004 | `/api/v1/health` latency inside the test suite (warm app, `TestClient`) | p95 ≤ 50 ms over 100 sequential requests |
| NFR-005 | Warm Vercel function response for `/api/v1/health` (preview) | p95 ≤ 500 ms over 20 requests from CI/dev machine |
| NFR-006 | Python function bundle size | ≤ 50 MB unzipped (Vercel limit is 250 MB; keep headroom) |
| NFR-007 | Layout | Welcome page renders without horizontal scroll at 375 px and 1280 px viewport widths |
| NFR-008 | Reproducibility | `uv sync --frozen` and `npm ci` succeed with no lockfile changes (`git diff --exit-code` clean afterwards) |

## 8. Data & Interfaces

### HTTP API (v1)

| Method & path | Query | 2xx response | Errors |
|---|---|---|---|
| `GET /api/v1/health` | — | `200 {"status":"ok","service":"canasta-api","version":"x.y.z"}` | 405 |
| `GET /api/v1/hello` | `name` (optional, 1–40 chars, pattern per FR-012; default `player`) | `200 {"message":"Welcome to Canasta, <name>!"}` | 422, 405 |
| `GET /api/openapi.json`, `GET /api/docs` | — | OpenAPI 3 / Swagger UI | — |

Error envelope (all non-2xx): `{"error":{"code":"validation_error|not_found|method_not_allowed|internal_error","message":"…","request_id":"…","details":[…]|null}}`.

### Environment variables

| Variable | Part | Default | Notes |
|---|---|---|---|
| `LOG_LEVEL` | api | `INFO` | DEBUG/INFO/WARNING/ERROR |
| `APP_ENV` | api | `local` | local/preview/production; included in every log line as `env` |
| `WEB_DIST_DIR` | api | unset | enables FR-018 |
| `VITE_API_BASE_URL` | web | `""` | build-time |
| `BASE_URL` | tests | unset | integration/E2E target |

### Extension points for later specs (informational, not implemented)

New backend features add routers under `routers/` and logic under `services/` or new top-level packages (`game`, `engine`, `ai`, `gamelog`) that must not import FastAPI (BR-005). The AI-engine interface (a `Protocol`) and the game/decision log are specified separately.

## 9. Verification Criteria

**Repository / tooling**
- VC-001: Fresh clone → `uv sync --frozen` in `apps/api` succeeds with `apps/web/node_modules` absent; `npm ci` in `apps/web` succeeds with `apps/api/.venv` absent. (FR-001)
- VC-002: `.python-version` = `3.12`, `.nvmrc` = `22`, both lockfiles tracked by git (`git ls-files` lists them); `uv run python --version` in `apps/api` prints `3.12.x`, and `node --version` under `.nvmrc` prints `v22.x`. (FR-002)
- VC-003: Each command listed in FR-003 exits 0 on the committed code; introducing an unused import in `apps/api/src` makes `ruff check` exit non-zero, a type error makes `ty check` exit non-zero, and a TS type error makes `npm run typecheck` exit non-zero. (FR-003, BR-008)
- VC-004: `make test` runs api and web test suites and exits non-zero if either fails. (FR-004)

**API**
- VC-010: `GET /api/v1/health` → `200`, JSON body keys exactly `status`,`service`,`version`, `status=="ok"`, `version` equals `canasta_api.__version__` and `[project].version` in `pyproject.toml`, and the endpoint works when `canasta_api` is not installed as a distribution (src on `sys.path` only). (FR-010)
- VC-011: `GET /api/v1/hello?name=Ana` → `200`, `{"message":"Welcome to Canasta, Ana!"}`; no `name` → message uses `player`; `name=José Núñez` (accented letters) → `200`. (FR-011)
- VC-012: `name=` (empty), `name` of 41 chars, `name=<script>`, `name=%20%20` (spaces only), `name=a;b` → each `422` with `error.code=="validation_error"`; `name` of exactly 40 chars → `200`; `name` of exactly 1 char → `200`. (FR-012)
- VC-013: `GET /api/v1/nope` → `404`, `error.code=="not_found"`, envelope shape per FR-014. (FR-013)
- VC-014: `POST /api/v1/health` → `405` with `error.code=="method_not_allowed"`; a route forced to raise `RuntimeError("secret-detail")` → `500`, body message `"Internal server error"`, body does not contain `secret-detail` or `Traceback`, and `request_id` equals the `X-Request-ID` response header. (FR-014)
- VC-015: Request with `X-Request-ID: abc-123` → response header `abc-123`; with value `bad id!` or 65 chars → response header is a valid UUID4 different from the input; with no header → response header is a valid UUID4. (FR-015)
- VC-016: One request → exactly one stdout line that parses as JSON with all FR-016 fields (including `env` and the `level` mapping), `outcome` correct for a 200, a 404 and a 500, and a request to `/api/v1/hello?name=Ana` produces a log whose serialized text does not contain `Ana`. (FR-016)
- VC-017: `LOG_LEVEL=VERBOSE` or `APP_ENV=staging` → `Settings()` raises a validation error whose text names the variable; defaults apply when unset; `WEB_DIST_DIR` unset → `None`. (FR-017)
- VC-018: With `WEB_DIST_DIR` set to a dir with `index.html` and `assets/app.js`: `GET /` → `200` HTML, `GET /game/xyz` → same `index.html`, `GET /assets/app.js` → file bytes, `GET /api/v1/health` → JSON health body (not HTML), `GET /api/nope` → `404` envelope (not HTML); `GET /%2e%2e/%2e%2e/etc/passwd` and `GET /../secret.txt` (file placed beside the dist dir) never return the outside file's content. With it unset: `GET /` → `404` envelope. (FR-018, BR-002)
- VC-019: `GET /api/openapi.json` → `200`, parses as JSON with `openapi` starting `3.` and both paths present; `GET /api/docs` → `200` HTML. (FR-019)

**Web**
- VC-030: Render welcome page → heading "Welcome to Canasta", labelled input "Your name" with `maxlength=40`, button "Ping API" present; mocked `fetch` has zero calls. (FR-030)
- VC-031: Type "Ana", click button with `fetch` resolving `{message:"Welcome to Canasta, Ana!"}` → during pending the button is disabled with text "Pinging…"; afterwards `role="status"` contains the message and the button is enabled with text "Ping API"; the request URL is `/api/v1/hello?name=Ana`. (FR-031)
- VC-032: `fetch` resolving `422` with envelope message "Invalid name" → `role="alert"` shows "Invalid name"; `fetch` rejecting (network error) → alert shows "Could not reach the server"; `fetch` resolving `200` with non-JSON body → alert shows "Could not reach the server"; in each case the button is re-enabled and no `role="status"` is shown. (FR-032)
- VC-033: Pasting a 60-character string → input value has length 40; request URL's `name` param has length ≤ 40. A name with spaces/accents (`José Núñez`) is URL-encoded correctly. (FR-033)
- VC-034: Client unit test: with `VITE_API_BASE_URL` = `""` → URL `/api/v1/hello?name=…`; with `https://x.test` → `https://x.test/api/v1/hello?name=…`; `npm run dev` with API running → `curl localhost:5173/api/v1/health` returns the health JSON. (FR-034)
- VC-035: axe run on the rendered page reports 0 serious/critical violations; Tab order is input → button; Enter on the input submits the form. (FR-035)

**Testing**
- VC-040: `pytest --collect-only -m unit|functional|interface` each collect ≥ 1 test; `--markers` lists all four markers; default `pytest` run deselects `integration`; with `BASE_URL` unset the integration test is reported as skipped, not failed; every test file under `unit/`, `interface/`, `functional/` uses plain functions (no `class Test…`) and every functional test has a docstring. (FR-040)
- VC-040b: Every file under `unit/`, `interface/`, `functional/` is checked by a meta-test (`tests/unit/test_layer_rules.py`) asserting that: unit tests import no `TestClient` and call no real clock; interface tests include a test per documented error code (`validation_error`, `not_found`, `method_not_allowed`, `internal_error`); and the functional test calls the real `create_app()`. (FR-045)
- VC-041: `pytest --cov=canasta_api --cov-fail-under=90` exits 0 on the committed code; `--cov-report=term-missing` shows no uncovered line in the exception handlers of `errors.py`. (FR-041)
- VC-042: `npm test` passes with network disabled; the client test file contains one test each for success, non-2xx envelope, invalid JSON and network failure. (FR-042)
- VC-043: `npm run test:coverage` exits non-zero when configured threshold (80% lines) is not met (verified by temporarily raising the threshold to 100% in a throwaway run). (FR-043)
- VC-044: `npm run e2e` (builds web, starts uvicorn with `WEB_DIST_DIR=apps/web/dist`) → Playwright test sees "Welcome to Canasta, Ana!" in `role="status"`; with `/api/**` aborted via `page.route`, clicking again shows `role="alert"`. Playwright's `webServer` config starts uvicorn; `npm run e2e` fails (non-zero) if the bundle was not built. (FR-044)

**CI**
- VC-050: PR touching only `apps/web/**` → `web` and `e2e` jobs run, `api` is skipped, `ci-ok` green; PR touching only `apps/api/**` → inverse; PR touching only `README.md` → `api`, `web`, `e2e` skipped and `ci-ok` green; PR touching `.github/workflows/ci.yml` → all run. (FR-050, FR-051)
- VC-051: A PR with a failing `web` test → `ci-ok` red and merge is blocked; cancelling the `api` job → `ci-ok` red. (FR-051, BR-007)
- VC-052: Modify `apps/api/uv.lock` dependency without regenerating `requirements.txt` → `api` job fails at the drift check; edit `pyproject.toml` dependencies without `uv lock` → `uv lock --check` fails. (FR-052)
- VC-053: Workflow YAML contains `permissions: contents: read`, `concurrency.cancel-in-progress: true`, a `timeout-minutes` on every job, and no `uses:` ref of `@main`/`@master`; `dependabot.yml` has ecosystems `uv`, `npm`, `github-actions` each weekly. (FR-053)
- VC-054: With `BASE_URL` set to a live preview, `pytest -m integration` passes; with the preview URL pointing at a 404 host it fails. (FR-054)

**Vercel**
- VC-060: Pushing a PR branch produces a preview URL; build log shows the web build command and publishes `apps/web/dist`; `GET <preview>/` → `200` HTML containing "Welcome to Canasta". (FR-060, FR-064)
- VC-061: `GET <preview>/api/v1/health` → `200` JSON; `GET <preview>/some/client/route` → `200` `index.html`; `GET <preview>/api/nope` → `404` JSON envelope (not HTML). (FR-061, BR-002)
- VC-062: Function logs on `<preview>/api/v1/health` show one JSON line with `env == "preview"`; `import canasta_api` succeeds in the deployed function (health returns 200, not 500); `WEB_DIST_DIR` is absent from the Vercel env. (FR-062, FR-064)
- VC-063: `curl -I <preview>/` shows the three security headers and `Cache-Control: public, max-age=0, must-revalidate`; `curl -I <preview>/assets/<hashed>.js` shows the immutable cache header; `curl -I <preview>/api/v1/health` shows `Cache-Control: no-store`. (FR-063)
- VC-064: Merging to `main` produces a production deployment where `GET /api/v1/health` is `200` and logs show `env == "production"`. (FR-064)
- VC-065: A commit changing only `specs/foo.md` → Vercel reports the build as skipped/ignored; a commit changing `apps/web/src/App.tsx` → build runs. (FR-065)
- VC-066: Function bundle size reported by Vercel build output ≤ 50 MB; `npm run build` output's initial JS ≤ 150 KB gzipped (check by script in the `web` CI job). (NFR-003, NFR-006)
- VC-067: Performance/layout NFR sweep — `TestClient` 100 sequential `health` calls p95 ≤ 50 ms (NFR-004); 20 sequential `curl` calls to the preview `health` p95 ≤ 500 ms (NFR-005); Playwright screenshots at 375 px and 1280 px show `scrollWidth <= clientWidth` (NFR-007); `uv sync --frozen && npm ci` followed by `git diff --exit-code` is clean (NFR-008); README quick start is ≤ 5 commands (NFR-001); CI run on warm cache is within NFR-002 limits.

**Business rules**
- VC-070: `grep -R "canasta_api" apps/web` and `grep -R "from \"\.\./\.\./api\|apps/web" apps/api` return nothing; the web part builds with `apps/api` directory removed. (BR-001)
- VC-071: `GET /api/docs`, `/api/openapi.json`, `/api/v1/*` all respond; `GET /v1/health` → `404`; all routes in `app.routes` start with `/api`. (BR-002, BR-003)
- VC-072: `git ls-files` contains `.env.example` files and no `.env`; `.gitignore` ignores `.env`; no file under `apps/web` references a non-`VITE_` env var at build time. (BR-004)
- VC-073: An import-linter style test (a unit test scanning `services/*.py` ASTs) asserts no module under `services/` imports `fastapi` or `starlette`; a domain `AppError` subclass raised from a service yields the mapped HTTP status through the handler. (BR-005)
- VC-074: GitHub repo secrets/Vercel tokens list is empty for this repo's Actions; workflow has no step referencing `VERCEL_`. (BR-006)
- VC-075: Branch protection on `main` lists exactly `ci-ok` as required status. (BR-007)

**End-to-end acceptance**
- VC-080: From a clean clone with only uv and Node 22 installed, a developer runs the README quick start (≤ 5 commands), opens the printed local URL, enters "Ana", presses "Ping API" and sees "Welcome to Canasta, Ana!"; then the same flow on the production Vercel URL after merge to `main` gives the same result, and `ci-ok` was green on the merged PR. (Whole spec; NFR-001)

## 10. Assumptions

- Source hosting and CI are GitHub / GitHub Actions; the Vercel project is connected through the Vercel GitHub integration.
- Vercel's Python runtime supports Python 3.12 and ASGI apps (FastAPI) exported as `app` from `api/index.py`, reading dependencies from `requirements.txt`. The exact `vercel.json` keys (`functions.includeFiles`, rewrites ordering) will be validated by the first preview deployment (VC-060…VC-062) and this spec updated if they differ.
- The Python package is named `canasta_api` (distribution `canasta-api`); renaming later is a mechanical change.
- Vite output is `apps/web/dist` and uses hashed filenames under `/assets/`.
- The free/hobby Vercel plan is sufficient (no cron, no long-running functions).
- Playwright's Chromium can be installed on `ubuntu-latest` runners.
- Async I/O is not used in this scaffold (handlers are `def`/trivially `async`; no blocking I/O exists yet). Whether the future game loop is async is decided in Spec 02.

## 11. Open Questions

- **OQ-1:** GitHub org/repo name and Vercel team/project name — needed only to wire branch protection and the Vercel integration (VC-064, VC-075); not blocking the code scaffold.

## 12. Changelog

- 0.1 (2026-11-08): Initial draft.
- 0.2 (2026-11-08): Review round 1 — fixed `docs/`→`specs/` path; version no longer from package metadata (Vercel has no installed dist); `--no-emit-project` in export; `env`/`level` in log events; static path-traversal rule; name validation edge cases; deterministic e2e failure case; CORS declared out of scope; VC-002 made verifiable.
