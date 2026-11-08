# Iteration 6: Vercel config, function shim, deployed integration test

Commit: see `git log`; message `feat(deploy): Vercel config, Python function shim and deployed-URL integration test`.

## Criteria
| Criterion | Command / check | Result |
|---|---|---|
| Local config test | `cd apps/api && uv run pytest` -> 144 passed, 2 deselected | PASS |
| VC-063 (local content) | `tests/unit/test_vercel_config.py` asserts header map, rewrites order, includeFiles, ignoreCommand | PASS (live curl pending manual) |
| Shim import | `tests/interface/test_vercel_shim.py`: subprocess, src removed from sys.path, no WEB_DIST_DIR, health version == `__version__` | PASS |
| VC-054 skip | `env -u BASE_URL uv run pytest -m integration -o addopts=""` -> 2 skipped | PASS |
| VC-054 fail on 404 host | `python -m http.server 8765` + `BASE_URL=http://127.0.0.1:8765 uv run pytest -m integration -o addopts=""` -> 2 failed (rc 1); server killed | PASS |
| VC-052 precondition | `uv lock --check` exit 0; `uv export --no-dev --no-hashes --no-emit-project --frozen \| diff - requirements.txt` empty | PASS |
| VC-074 | `grep -rn VERCEL_ .github` (no workflows exist yet) -> none | PASS (re-verify in iteration 7) |
| Regression | `uv sync --frozen`, ruff check, ruff format --check, ty check, pytest --cov gate (100%); `make lint` 0; `make test` (144 api + 20 web) | PASS |
| VC-060, 061, 062, 063 (live), 064, 065, 066 (bundle size), 067 NFR-005, VC-054 vs live preview | need a real Vercel project (OQ-1) | pending manual |

## Files
Added: `vercel.json`, `api/index.py`, `apps/api/requirements.txt`, `apps/api/tests/unit/test_vercel_config.py`, `apps/api/tests/interface/test_vercel_shim.py`.
Changed: `tests/integration/test_deployed_health.py` renamed to `test_deployed.py` (+ home-page test), CONTEXT.md, DECISIONS.md (D-014).
Deleted: none (rename only).

## Deviations
- Header rules for `/` and `/index.html` are separate entries (VC-063 checks `/`).
- Shim test lives in the interface layer (meta-test forbids TestClient in unit); config test in unit.

## Gotchas
- `apps/api` ruff/ty do not cover `api/index.py` (outside project).
- Shim test uses `sys.executable` so it needs the dev venv (fastapi, httpx).
- Repo root from tests: `Path(__file__).resolve().parents[4]`.
- Port 8000 untouched; 404-host check used 8765.

## For the next iteration
- CI api job: add `uv lock --check` and the requirements drift diff; changes filter includes `api/**` and `vercel.json`.
- No workflow may reference `VERCEL_` (add to the CI config test).
- README (iteration 8) must document Vercel settings: Root Directory = repo root, env `APP_ENV`, no `WEB_DIST_DIR`.
