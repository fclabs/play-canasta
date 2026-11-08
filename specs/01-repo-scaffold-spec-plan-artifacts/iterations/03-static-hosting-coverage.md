# Iteration 3: Static web hosting, test-layer rules and coverage gate

Commit: see `git log`; message `feat(api): optional static web serving and enforced test layering/coverage`.

## Criteria (run from /Users/fede/devel/fclabs/play-canasta/apps/api)
| Criterion | Command / check | Result |
|---|---|---|
| VC-018 (static) | `tests/interface/test_static_hosting.py` (19 tests: `/`, `/game/xyz`, `/assets/app.js`, `/api/v1/health` JSON, `/api/nope` envelope, 8 traversal paths incl. `/../secret.txt`, `/%2e%2e/%2e%2e/etc/passwd`; unset -> 404 envelope) with secret file beside tmp dist | PASS |
| VC-040 | `pytest --collect-only -q -m unit\|functional\|interface -o addopts=""` -> 83 / 2 / 51 tests; `pytest --markers` lists all four; default run "136 passed, 1 deselected"; `pytest -m integration -rs -o addopts=""` -> 1 skipped (BASE_URL not set) | PASS |
| VC-040b | `tests/unit/test_layer_rules.py` (12 tests) | PASS |
| VC-041 | `uv run pytest --cov=canasta_api --cov-fail-under=90 --cov-report=term-missing` exit 0, total 100%, `errors.py` 0 missing | PASS |
| NFR-004 | `tests/interface/test_health_latency.py` p95 <= 50 ms over 100 calls | PASS |
| Gates | `rm -rf .venv && uv sync --frozen`; `uv run ruff check .`; `uv run ruff format --check .`; `uv run ty check`; `uv run pytest` (136 passed) | PASS |
| Artifacts | CONTEXT.md, DECISIONS.md (D-008, D-009), this record | PASS |

## Files
Added: `src/canasta_api/static.py`, `tests/unit/{test_static,test_layer_rules}.py`, `tests/interface/{test_static_hosting,test_health_latency}.py`, `tests/integration/test_deployed_health.py`, this record.
Changed: `main.py` (mount static last), `pyproject.toml` + `uv.lock` (dev dep `pytest-cov`), `tests/interface/conftest.py` (`dist_dir`, `static_client`), `tests/unit/test_request_logging.py` (StdoutHandler failure branch), CONTEXT.md, DECISIONS.md.
Deleted: none.

## Deviations
- Coverage flags not in `addopts` (D-009).
- Integration stub requires `-o addopts=""` to run (default addopts deselects it).

## Gotchas
- httpx normalizes `/../x` client-side, so `%2f`-encoded variants and symlink unit test cover the server-side defence.
- Meta-test scans unit tests for real-clock calls by attribute name; use injected `fixed_clock`/`fake_timer` there.
- Route-prefix test only holds for the static-off app.

## For the next iteration
- Web build output (`apps/web/dist`) is served by setting `WEB_DIST_DIR`; use fixtures `dist_dir`/`static_client` as a model.
- Iteration 5 e2e: start uvicorn with `WEB_DIST_DIR=apps/web/dist`.
- Iteration 6: extend `tests/integration/test_deployed_health.py`; Vercel must not set `WEB_DIST_DIR`.
- Iteration 7 CI should run the full coverage command.
