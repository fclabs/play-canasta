# Iteration 8: Documentation (final)

Commit: see `git log`; message `docs: README and user documentation for the scaffold`.

## Criteria
| Criterion | Command / check | Result |
|---|---|---|
| VC-080 (local) | clean `git worktree` of HEAD + docs, fresh `.venv`/`node_modules`; README quick start `make install`, API (`uvicorn --reload`) and `npm run dev` on alternate ports 8001/5199 (8000 held by an unrelated process, vite proxy edited only in the scratch tree); Playwright typed "Ana", pressed "Ping API", read status "Welcome to Canasta, Ana!"; `curl /api/v1/hello?name=Ana` through the proxy matched | PASS (ports differ from README defaults) |
| getting-started commands | in the clean tree: build, single-process mode (`/`, `/game/x` HTML, `/api/nope` envelope, health), `make test`, `make lint`, API coverage gate (100%), web `test:coverage` (90.7%), per-marker runs (100/2/52), integration skip, `uv lock --check`, export diff, regenerate requirements (no diff), `prettier --write` (unchanged), `npm run e2e` (4 passed), add-endpoint recipe (155 passed, ruff/ty clean) | PASS |
| VC-067 / NFR-001 | README quick start has 4 commands | PASS |
| Docs exist | README.md, docs/{overview,getting-started,architecture,deployment,limitations}.md | PASS |
| No artifact refs | `grep -rn "artifacts\|-plan\|01-repo-scaffold" README.md docs` -> none | PASS |
| Decisions covered | D-001..D-003, D-005..D-016 in architecture/deployment/limitations; D-004 layout line; D-017 internal | PASS |
| Final acceptance test | see report in the commit conversation; all gates exit 0 on the committed tree | PASS |

## Files
Changed: `README.md` (rewritten), CONTEXT.md, DECISIONS.md (D-017). Added: `docs/*.md` (5), this record. Deleted: none. No code changes.

## Deviations
- Quick start verified on ports 8001/5199 instead of 8000/5173 (8000 occupied; not killed).
- No code touched.

## Gotchas
- BSD `sed -i` needs `''` on macOS (matters only for maintainers' scripts).
- Docs say Playwright browsers need `npx playwright install chromium` once.

## Manual checks still pending (post-merge)
- GitHub: VC-050 (path-scoped PRs run/skip expected jobs, `ci-ok` green), VC-051 (failing web test and cancelled api job -> `ci-ok` red), VC-075 (branch protection requires exactly `ci-ok`), VC-074 (no Actions secrets), VC-052 on a real run, NFR-002 timing.
- Vercel: VC-060..VC-065 (live curl, headers, rewrites, build from repo root), VC-066 function bundle <= 50 MB, NFR-005 (p95 <= 500 ms), VC-054 against a live preview, VC-080 production half. Unverified `vercel.json` keys: `functions.includeFiles`, `ignoreCommand`, header sources for `/`, rewrite destination `/api/index`.
- `make dev-api` against a real free 8000 (unverified locally).

## For the next iteration
- None (final). After pushing, run the pending checks above and update `vercel.json`, its test and `docs/limitations.md` if an assumption is wrong.
