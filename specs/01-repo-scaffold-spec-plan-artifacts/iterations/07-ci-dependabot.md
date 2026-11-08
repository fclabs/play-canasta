# Iteration 7: GitHub Actions CI and Dependabot

Commit: see `git log`; message `ci: path-aware GitHub Actions workflow with ci-ok gate and Dependabot`.

## Criteria
| Criterion | Command / check | Result |
|---|---|---|
| VC-053 | `cd apps/api && uv run pytest tests/unit/test_ci_config.py` (permissions, concurrency, timeouts, pinned actions, ci-ok wiring, path filters, dependabot weekly) | PASS (10 tests; full run 154 passed) |
| VC-074 | `grep -rn VERCEL_ .github` -> no matches (rc 1) + test `test_no_workflow_references_vercel_secrets_or_tokens` | PASS |
| VC-052 | `uv lock --check` rc 0; `uv export --no-dev --no-hashes --no-emit-project --frozen \| diff - requirements.txt` rc 0 (after adding pyyaml) | PASS |
| API gates | `uv sync --frozen`, `ruff check .`, `ruff format --check .`, `ty check`, `pytest --cov=canasta_api --cov-fail-under=90` (100%) | PASS |
| Web gates | `npm ci`, `npm run lint`, `format:check`, `typecheck`, `test:coverage`, `build` (bundle 67.0 KB gz <= 150) | PASS |
| e2e | `cd apps/web && npm run e2e` -> 4 passed (port 8123) | PASS |
| YAML validity | `actionlint .github/workflows/ci.yml` (installed locally) | PASS |
| VC-050, VC-051, VC-075 | need a real GitHub repo | pending manual |

## Files
Added: `.github/workflows/ci.yml`, `.github/dependabot.yml`, `apps/api/tests/unit/test_ci_config.py`.
Changed: `apps/api/pyproject.toml` (dev dep pyyaml), `apps/api/uv.lock`, CONTEXT.md, DECISIONS.md (D-015, D-016).
Deleted: none.

## Deviations
- The workflow file is listed in both path filters (the "api" filter also feeds `e2e`), per scope.
- `actions/setup-python@v5` added next to setup-uv so Python 3.12 is explicit.
- Steps pass `uv sync --frozen`; Playwright/e2e does not run the `api`/`web` jobs first (parallel).

## Gotchas
- PyYAML parses the `on:` key as `True`; the test does not read triggers.
- Skipped jobs report `skipped`, which `ci-ok` treats as pass; do not add `needs` on `ci-ok` that would be skipped with `if` lacking `always()`.
- Workflow has never run on GitHub; action versions are unverified until the first push.

## For the next iteration
- Docs (8): describe CI jobs, `ci-ok`, branch protection setup (require exactly `ci-ok`), Dependabot, and list the manual checks below as limitations.
- Manual checks (pending manual): VC-050 open PRs touching only `apps/web/**` (web+e2e run, api skipped), only `apps/api/**` (api+e2e run, web skipped), only `README.md` (all skipped), and `.github/workflows/ci.yml` (all run); `ci-ok` green each time. VC-051 failing web test -> `ci-ok` red; cancel `api` -> red. VC-075 branch protection on `main` requires exactly `ci-ok`. VC-074 repo Actions secrets empty. NFR-002 timing on warm cache.
