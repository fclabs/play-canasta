# Architecture

## Layout

```
apps/api/
  pyproject.toml (hatchling build, `src` layout; shared constants live in settings.py),
  uv.lock, .python-version, requirements.txt (generated for Vercel)
  src/canasta_api/
    __init__.py      __version__ (single source of the version)
    settings.py      Settings (env-backed) and shared constants
    main.py          create_app(settings=None) and the module-level `app`
    errors.py        AppError types, status mapping, error handlers
    logging.py       JSON log formatter and the request middleware
    static.py        optional static hosting of the web bundle
    routers/         HTTP routes (health, hello)
    schemas/         Pydantic request/response models (incl. the error envelope)
    services/        business logic, no HTTP
  tests/{unit,functional,interface,integration}/
apps/web/
  src/api/           client (`getHello`) and response types
  src/pages/         Welcome page
  e2e/               Playwright smoke tests
  scripts/check-bundle-size.mjs
api/index.py         Vercel function entrypoint
```

## Layers

Dependencies point one way: `routers` -> `services` and `schemas`; `services` depend on
neither routers nor HTTP frameworks.

- **Parts are independent.** The web part never mentions the API package and the API never
  mentions the web sources. They communicate only through HTTP. Either builds, tests and
  deploys without the other (the API reads a built bundle only if you set `WEB_DIST_DIR`).
- **Everything lives under `/api`.** Every route, including docs (`/api/docs`) and the
  OpenAPI schema (`/api/openapi.json`), starts with `/api`. This is why a single rewrite
  rule works on Vercel and why the Vite proxy needs one entry. FastAPI's default Swagger
  OAuth2 redirect is moved to `/api/docs/oauth2-redirect` for the same reason; ReDoc is
  disabled. A test checks that no route escapes the prefix (the only exception is the
  optional static catch-all).
- **Domain routes live under `/api/v1`.** Health and hello are `/api/v1/health` and
  `/api/v1/hello`. `/v1/health` (no `/api`) is a 404.
- **Services never import `fastapi` or `starlette`.** A test parses the source to
  enforce it. Services raise `AppError` subclasses, which carry a `code`, a message and
  optional details but no HTTP status. The status lives in a mapping (`ERROR_STATUS` in
  `errors.py`), so business code can later be reused outside HTTP.

## Error envelope

Every non-2xx response, including unknown paths, wrong methods, validation failures and
crashes, has this body:

```json
{"error": {"code": "validation_error", "message": "Request validation failed",
           "request_id": "…", "details": [{"field": "name", "location": "query",
           "message": "…", "type": "…"}]}}
```

| Situation | Status | `code` |
|---|---|---|
| Invalid request input | 422 | `validation_error` (`details` lists each offending `field`) |
| Unknown path | 404 | `not_found` |
| Wrong method (keeps the `Allow` header) | 405 | `method_not_allowed` |
| Other framework HTTP errors | as raised | `http_error` |
| Unhandled exception | 500 | `internal_error`, message always "Internal server error" |
| An `AppError` | from `ERROR_STATUS` | the error's own `code` |

`details` is `null` unless there is something to list. The 500 body never leaks the
exception text.

**Adding an error type**: subclass `NotFoundError` (404) or `ConflictError` (409) in
`errors.py`, set `code` and `default_message`, and raise it from a service. For a new
status, subclass `AppError` and register the class in `ERROR_STATUS`; an unregistered
subclass answers as a generic 500.

Why the 500 is produced by middleware rather than an `Exception` handler: Starlette runs
`Exception` handlers outside user middleware, so the `X-Request-ID` header and the log
line would be lost. The request middleware catches the exception itself and sends the
envelope, so crashes look like every other response.

## Request ID and logging

- Every response has an `X-Request-ID` header. An incoming `X-Request-ID` is kept only if
  it matches `[A-Za-z0-9._-]{1,64}` (so it is safe to log); otherwise a fresh UUID4 is
  generated. The same ID appears in the error envelope.
- Each request writes exactly one JSON line to stdout (the "wide event"), e.g.:

  ```json
  {"timestamp":"2026-01-02T03:04:05+00:00","service":"canasta-api","env":"local",
   "request_id":"…","method":"GET","path":"/api/v1/hello","status_code":200,
   "latency_ms":1.234,"outcome":"ok","level":"INFO","event":"http_request"}
  ```

  `path` never includes the query string (it can hold personal data such as names).
  `outcome` and `level` follow the status (5xx logs at ERROR, 4xx at WARNING); crashes add
  `error_type` (the class name only). Raising `LOG_LEVEL` above `INFO` hides the
  successful-request lines.
- The middleware is deliberately the outermost user middleware, so it sees 404/405/422
  and crashes. If you add middleware, register it before it in `create_app`.
- It is plain stdlib `logging` with a stdout handler that looks up `sys.stdout` at write
  time (so tests can capture it); clock, timer and UUID source are injectable.

## Settings

`Settings` reads `LOG_LEVEL`, `APP_ENV` and `WEB_DIST_DIR` from the environment or
`.env`. Fields are validated with the variable's own name, so a bad value fails startup
with a message such as one naming `LOG_LEVEL`. There is no global settings object:
`create_app(settings)` takes them as an argument, which is how tests inject
configuration. The module-level `app` (what uvicorn and Vercel import) loads them from
the environment at import time.

## Static hosting

When `WEB_DIST_DIR` points at a directory containing `index.html`, `create_app` adds one
hidden catch-all `GET /{path}` route after all API routes:

- An existing file inside the directory is served as is.
- Any other path (including client-side routes like `/game/xyz`) returns `index.html`.
- `/api` and `/api/...` always go to the API; unknown API paths return the 404 envelope,
  never HTML.
- Paths that escape the directory (`..`, encoded variants, symlinks pointing outside,
  directories, NUL bytes) fall back to `index.html` and never leak other files.
- Non-GET requests to non-API paths return the 405 envelope.

It is one custom route rather than Starlette's `StaticFiles` mount because a mount does
not give a single-page-app fallback, shadows route ordering, and 404s in HTML rather than
the envelope. With the variable unset, unknown non-API paths return the 404 envelope.

## API and web contract

- `GET /api/v1/health` -> `{"status":"ok","service":"canasta-api","version":"<__version__>"}`.
- `GET /api/v1/hello?name=<name>` -> `{"message":"Welcome to Canasta, <name>!"}`. When
  `name` is omitted it is `player`. A name is valid if it is 1 to 40 characters, not just
  spaces, and made only of letters, digits (Unicode allowed) and the punctuation
  ` '-_`. Anything else is a 422 envelope. The name is not trimmed. The rules use
  `str.isalpha()`/`isdecimal()` in a validator because Unicode-aware regex classes
  disagree with them (for example on `_` and characters like "²").
- The client calls `${VITE_API_BASE_URL}/api/v1/hello?name=<url-encoded>`; the base URL
  is empty by default (same origin) and read when called. `getHello` throws an `ApiError`
  whose message is ready to show: the envelope's `message` when there is one, otherwise
  "Could not reach the server" (network errors, invalid JSON, a 200 without a string
  `message`). The page just renders it.
- The page: heading "Welcome to Canasta"; textbox "Your name" (max 40 characters); button
  "Ping API" (disabled and "Pinging…" while waiting); the result appears as `role="status"`
  on success and `role="alert"` on failure.
- No CORS: the API is same-origin only (Vite proxy, FastAPI static mode, Vercel rewrites).

## Testing model

- API tests are plain functions with Given/When/Then/Clean comments, one marker per module
  (`unit`, `functional`, `interface`, `integration`) matching its directory. `integration`
  is excluded by default because it needs a deployed URL.
- A meta-test enforces the rules: no test classes; unit tests do not use `TestClient` or
  read the real clock (use the `fixed_clock`, `fake_timer`, `fixed_uuid` fixtures);
  interface tests exist for each error code; functional tests have business docstrings.
- Coverage gates: API 90% (`--cov-fail-under` run explicitly, not in default options so
  the everyday run stays fast), web 80% lines.
- The web bundle size check is part of `npm run build` (the build script chains it), so
  CI's build step enforces it. No extra npm script exists for it.
- `npm run e2e` builds first; the Playwright config only verifies the bundle exists and
  starts the API on a fixed port (8123) to avoid clashing with dev servers.
- `make test` and `make lint` run both parts even if the first fails and exit non-zero if
  either failed, so you see every problem at once.

## Versioning

The API version is `canasta_api.__version__`, which must equal `[project].version` in
`pyproject.toml` (a test checks this). It is never read from installed package metadata,
because the project is not installed on Vercel.
