# Iteration 4: Web client

Commit: see `git log`; message `feat(web): welcome page calling the hello API, with component tests`.

## Criteria (from /Users/fede/devel/fclabs/play-canasta/apps/web unless noted)
| Criterion | Command / check | Result |
|---|---|---|
| VC-001 (web) | moved `apps/api/.venv` away, `rm -rf node_modules && npm ci` exit 0, `npm test` ok; venv restored | PASS |
| VC-003 (web) | `npm run lint`, `format:check`, `typecheck`, `test` all exit 0 | PASS |
| VC-030..033 | `src/pages/Welcome.test.tsx` (heading/label/maxlength/no fetch; pending+status; 422 alert; network + invalid JSON fallback; 60-char paste -> 40; `José Núñez` encoded) | PASS |
| VC-034 (unit) | `src/api/client.test.ts` empty base, `https://x.test` base. Proxy curl: deferred to iteration 5 | PASS (unit) |
| VC-035 | vitest-axe: 0 serious/critical; Tab input->button; Enter submits | PASS |
| VC-042 | `npm test`: 20 tests, fetch mocked; client has success, envelope, invalid JSON, network tests | PASS |
| VC-043 | `npm run test:coverage` exit 0 (lines 90.7%); with `lines: 100` exit 1; reverted to 80 | PASS |
| VC-066 | `npm run build` -> "initial JS 67.0 KB gzipped (limit 150 KB)"; limit lowered temporarily -> exit 1 | PASS |
| VC-070 | `grep -R canasta_api apps/web` (excl. node_modules) empty; no api->web refs | PASS |
| VC-072 | `.env.example` present, `.env` ignored (git check-ignore), only `VITE_API_BASE_URL` referenced | PASS |
| API regression | ruff check/format, ty, pytest (136 passed), coverage gate 100% | PASS |
| Artifacts | CONTEXT.md, DECISIONS.md (D-010, D-011), this record | PASS |

## Files
Added: everything under `apps/web` (config, `scripts/check-bundle-size.mjs`, `src/**`, lockfile).
Changed: CONTEXT.md, DECISIONS.md. Deleted: none.

## Deviations
- `e2e` script is a placeholder (`exit 1`), as allowed.
- "Web builds with apps/api removed" checked by moving `.venv` and by grep, not by deleting `apps/api`.

## Gotchas
- Local Node is v26; engines `>=22 <23` only warns. npm prints an install-scripts warning for fsevents (harmless).
- `vitest-axe` needs `src/vitest-axe.d.ts` for matcher typings; matchers registered in `src/test-setup.ts`.
- `import.meta.env.VITE_API_BASE_URL` is read inside `getHello` so `vi.stubEnv` works.
- Prettier ignores package-lock.json; `.prettierignore` also covers dist/coverage.

## For the next iteration
- Playwright: use the accessible contract in CONTEXT.md (Public interfaces). Serve built `apps/web/dist` through uvicorn with `WEB_DIST_DIR=apps/web/dist`, or `npm run dev` for the proxy check.
- Replace the `e2e` script placeholder with the Playwright command (name must stay `e2e`); `.gitignore` already covers playwright-report/test-results.
- Verify no horizontal scroll at 375/1280 px and `curl localhost:5173/api/v1/health` via the proxy.
- Root Makefile `dev-web` -> `npm run dev`; install -> `npm ci`.
