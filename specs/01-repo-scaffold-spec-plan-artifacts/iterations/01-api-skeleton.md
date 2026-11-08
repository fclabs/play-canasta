# Iteration 1: API skeleton (health + hello happy path)

Commit: see `git log` (single commit, subject below); message `feat(api): FastAPI skeleton with health and hello endpoints`.

## Criteria (all run from /Users/fede/devel/fclabs/play-canasta/apps/api unless noted)
| Criterion | Command / check | Result |
|---|---|---|
| VC-001 (api) | `rm -rf .venv && uv sync --frozen` with no `apps/web` dir at all | PASS |
| VC-002 | `cat .python-version` = 3.12; `uv run python --version` = 3.12.10; `uv.lock` untracked->committed | PASS |
| VC-003 (api) | `uv run ruff check .`, `ruff format --check .`, `ty check`, `pytest` all exit 0; injected `import os` -> ruff exit 1; injected `x: int = "a"` -> ty exit 1 (both reverted) | PASS |
| VC-010 | `tests/interface/test_health_api.py`, `tests/unit/test_version.py`; src-only run: `PYTHONPATH=apps/api/src uv run --no-project --with fastapi --with pydantic-settings --with httpx python ...` returns health JSON, `canasta-api` metadata absent | PASS |
| VC-011 | `tests/interface/test_hello_api.py` (Ana, default player, `José Núñez`) | PASS |
| VC-012 | same file: empty, 41 chars, `<script>`, spaces-only, `a;b` -> 422; 1 and 40 chars -> 200 (status only) | PASS |
| VC-017 | `tests/unit/test_settings.py` (defaults, env, `LOG_LEVEL`/`APP_ENV` errors name var) | PASS |
| VC-019 | `tests/interface/test_openapi_and_routing.py` | PASS |
| VC-071 | same file: all `Route` paths start with `/api`; `/v1/health` -> 404 | PASS |
| VC-073 (service AST half) | `tests/unit/test_services_layering.py` | PASS |
| VC-040 (partial, early) | `pytest --markers` lists 4 markers; `-m unit/functional/interface` collect 16/1/15; integration deselected by default | PASS |
| Artifacts | CONTEXT.md, DECISIONS.md, this record | PASS |

Final full run: `uv run pytest` -> 32 passed.

## Files
Added: `.gitignore`, `.editorconfig`, `README.md`, all of `apps/api/**` (listed in CONTEXT.md file map, incl. `uv.lock`), `specs/**` (previously untracked), artifacts.
Changed/deleted: none.

## Deviations
- None from the plan. Extras kept minimal: `swagger_ui_oauth2_redirect_url` moved (D-003), ReDoc disabled.
- Integration test file not created (allowed stub; iteration 6).

## Gotchas
- FastAPI's default `/docs/oauth2-redirect` route breaks BR-002 unless relocated.
- `uv run --no-project` from inside `apps/api` still sees `.venv`; verify "not installed" from another cwd.
- Starlette emits a `StarletteDeprecationWarning` about `httpx` vs `httpx2` in TestClient; harmless.
- uv installs the project editable, so `importlib.metadata` would work locally but not on Vercel; never use it.
- `Settings` fields use alias names; construct with `Settings(_env_file=None)` in tests.

## For the next iteration
- Add `errors.py`, `logging.py`, `schemas/errors.py`; register in `create_app` (signature `create_app(settings: Settings | None = None)`; `app.state.settings` available to middleware).
- Interface hello 422 tests currently assert status only; upgrade to envelope assertions. Interface `client` fixture in `tests/interface/conftest.py`, `app`/`settings` in `tests/conftest.py`.
- `log_level` setting is already loaded; use `settings.app_env` for the `env` log field.
- Handler-mapping half of VC-073: add an `AppError` subclass raised from a service/route via a test-only app.
- Constants: add new `Final`s to `canasta_api/settings.py` (e.g. request-ID regex).
- Commands are in CONTEXT.md; all must stay green.
