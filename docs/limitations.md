# Limitations and gotchas

## Not yet verified on real infrastructure

The CI workflow and the Vercel configuration were validated locally only (configuration
content tests, `actionlint`, local end-to-end runs). Until the first push and deployment,
treat these as unconfirmed:

- **GitHub Actions** has never run. To confirm: open pull requests touching only
  `apps/web/**` (web and e2e run, api skipped), only `apps/api/**` (api and e2e run, web
  skipped), only `README.md` (all skipped) and the workflow file (all run); `ci-ok` must be
  green each time. Make a web test fail and cancel the `api` job to see `ci-ok` go red.
  Check that repository Actions secrets are empty, that a changed `uv.lock` without a
  regenerated `requirements.txt` fails the `api` job, and that a warm-cache run stays under
  8 minutes (api 3, web 4).
- **Branch protection** on `main` requiring exactly `ci-ok` must be set up by hand.
- **`vercel.json`** keys that can only be proven by a real deployment:
  `functions."api/index.py".includeFiles`, `ignoreCommand`, the header `source` patterns
  for `/` and `/index.html`, and the rewrite destination `/api/index`. On the first preview
  confirm: the build uses the repository root; `/api/v1/health` returns JSON with the
  right version; `/` and an unknown client path serve the app while `/api/nope` returns the
  JSON 404 envelope; response headers match the [headers table](deployment.md#headers);
  the function bundle is under 50 MB; health p95 stays under 500 ms over 20 requests; and
  the welcome flow works on the production URL after merging to `main`. If a key proves
  wrong, update `vercel.json`, its content test and these docs.
- `ignoreCommand` compares with `HEAD^`; on shallow clones or a first commit it fails open
  and builds.

## Out of scope for the scaffold

- Any Canasta rules, cards, scoring, turns or game state, AI players, and game or decision
  logging. The request log is not a game log.
- Authentication, accounts, databases, WebSockets or other real-time transport.
- **CORS**: no CORS middleware. The API only works same-origin (Vite proxy, FastAPI static
  mode, Vercel rewrites). A client on another origin would need CORS added deliberately.
- Custom domain, analytics, monitoring and alerting, i18n, PWA/offline.
- Deploying from GitHub Actions (the Vercel Git integration deploys).

## Known gaps

- `make dev-api` and the Vite proxy both assume port 8000. If the port is taken, start the
  API on another port (`uv run uvicorn canasta_api.main:app --port 8001`) and edit the proxy
  target in `apps/web/vite.config.ts` locally, or use single-process mode on any port.
- E2E runs in Chromium only, on port 8123, and Playwright browsers must be installed
  separately.
- Node is pinned to 22 (`engines >=22 <23`); other majors only warn. CI uses Node 22.
- The OpenAPI schema still documents FastAPI's default 422 body, not the error envelope
  (the real responses use the envelope).
- The bundle-size check only counts JavaScript referenced from `dist/index.html`; dynamic
  imports are not counted (there are none today).
- Static serving sets no cache headers; on Vercel the CDN serves assets, not this path.
- Error codes are asserted by a meta-test that looks for string literals in interface
  tests, which is a heuristic, not a full proof.
- `LOG_LEVEL=WARNING` or `ERROR` suppresses the request log lines of successful requests.
- `errors.py` imports FastAPI, so a service that imports it is HTTP-aware indirectly; the
  source-parsing test only catches direct imports of `fastapi`/`starlette`.
- Dependabot and CI use version tags for actions, not commit SHAs.

## Gotchas

- Every route must start with `/api`. Any new FastAPI default route has to be moved under
  it (the Swagger OAuth2 redirect already was).
- Never use `importlib.metadata` for the version, and always export `requirements.txt`
  with `--no-emit-project` (see [deployment](deployment.md#troubleshooting)).
- `Settings` fields are validated through their environment names; in tests build them with
  `Settings(_env_file=None)` to ignore any local `.env`.
- Test module file names must stay unique across the `unit`, `functional`, `interface`
  and `integration` folders (there are no `__init__.py` files in `tests`).
- Unit tests may not call the real clock (`now`, `time`, `perf_counter`, `sleep`, ...);
  use the injected fixtures. Timing tests belong to the interface layer.
- Add new middleware before `RequestContextMiddleware` in `create_app`, so it stays the
  outermost one.
- The static catch-all route must be added last in `create_app`.
- `httpx` normalizes `/../x` on the client, so the traversal tests also use encoded forms.
- `uv run --no-project` inside `apps/api` still sees `.venv`; check "not installed" from
  another directory.
- `uv sync` installs the project in editable mode; that is why Vercel needs the export flag
  and the shim.
- PyYAML reads the workflow `on:` key as a boolean; the CI config test never reads triggers.
- The test run prints a harmless Starlette deprecation warning about `httpx`, and jsdom
  prints "HTMLCanvasElement getContext not implemented" from the accessibility check.
- npm prints an install-scripts warning for `fsevents` on macOS; it is harmless.
- Playwright's webServer uses `uv run --project ../api`, so `uv` must be on `PATH`.
- PyYAML is a dev-only dependency (CI config test) and is not part of `requirements.txt`.
