# Iteration 5: E2E smoke and Makefile

Commit: see `git log`; message `test: Playwright e2e smoke against FastAPI-served bundle; root Makefile`.

## Criteria
| Criterion | Command / check | Result |
|---|---|---|
| VC-044 | `cd apps/web && npm run e2e` -> build + 4 Playwright tests passed, exit 0 | PASS |
| VC-004 | `make test` exit 0 (136 api + 20 web); broken api test -> exit 2; broken web test -> exit 2; reverted, clean run exit 0 | PASS |
| VC-034 (proxy) | `make dev-api` could not bind: port 8000 held by an unrelated `python -m http.server 8000` (not killed). Equivalent check: uvicorn on 8001 + vite with a temporary config proxying to 8001 -> `curl localhost:5173/api/v1/health` = `{"status":"ok","service":"canasta-api","version":"0.1.0"}` 200. Temp config deleted | PASS (workaround; `make dev-web`/vite proxy code unchanged since iteration 4) |
| VC-067 layout | e2e tests at 375 and 1280 px assert `scrollWidth <= clientWidth` | PASS |
| VC-067 NFR-008 | `make install` (uv sync --frozen, npm ci) then `git diff --exit-code` on files not edited by this iteration: clean | PASS |
| Regression | api ruff, format, ty, pytest --cov gate (100%); web lint, format:check, typecheck, test:coverage (20 tests); `make lint` exit 0 | PASS |
| Artifacts | CONTEXT.md, DECISIONS.md (D-012, D-013), this record | PASS |

## Files
Added: `Makefile`, `apps/web/playwright.config.ts`, `apps/web/e2e/smoke.spec.ts`.
Changed: `apps/web/package.json` (+lock; `e2e` script, `@playwright/test`, `@types/node`), `vite.config.ts` (vitest exclude e2e), `tsconfig.json` (include e2e + playwright config), `eslint.config.js` (ignore report dirs), `.prettierignore`, CONTEXT.md, DECISIONS.md.
Deleted: none.

## Deviations
- VC-034 proxy verified on port 8001 because 8000 was occupied locally (see above).
- `@types/node` added (config uses node APIs); no other extras.

## Gotchas
- `make dev-api` and the vite proxy both assume port 8000.
- Playwright 1.65 downloaded chromium-headless-shell build 1254 locally.
- The e2e API server logs at WARNING to keep output quiet.
- npm lock changed only by adding the two devDependencies.

## For the next iteration
- CI e2e job: `cd apps/web && npm ci && npx playwright install --with-deps chromium && npm run e2e` (also needs uv + `uv sync --frozen` in apps/api first, since webServer uses `uv run --project ../api`). `npm run e2e` builds itself. Set `CI=1` for retries/github reporter; upload `apps/web/playwright-report` on failure if desired.
- Makefile targets: install, dev-api, dev-web, test, lint.
- Iteration 6 must not break `WEB_DIST_DIR`-based static serving.
