# Deployment and CI

## Vercel

The repository is deployed as one Vercel project through the Vercel Git integration: a
merge to `main` is a production deploy, a pull request gets a preview. GitHub Actions
does not deploy and must not hold Vercel tokens or reference `VERCEL_*` variables.

### Project settings

| Setting | Value |
|---|---|
| Root Directory | the repository root (not `apps/web`) |
| Install / Build / Output | taken from `vercel.json` (`npm ci --prefix apps/web`, `npm run build --prefix apps/web`, `apps/web/dist`) |
| Environment variable `APP_ENV` | `preview` (Preview), `production` (Production) |
| `WEB_DIST_DIR` | do not set; the CDN serves the static files |

The Python function installs the repository-root `requirements.txt`, which only contains `-r apps/api/requirements.txt` (a lockfile export; Vercel looks for dependencies at the project root, so the export alone in `apps/api/` is not found). Keep it in
sync when dependencies change: see [getting-started](getting-started.md#regenerate-requirementstxt).

### How a request is routed

- `api/index.py` is the only function. It adds `apps/api/src` to `sys.path` and exposes
  the FastAPI `app`.
- `functions."api/index.py".includeFiles = "apps/api/src/**"` ships the sources with the
  function.
- Rewrites, in order: `/api/(.*)` -> `/api/index` (the function), then everything that is
  not under `/api/` -> `/index.html` (single-page-app fallback). Real static files, such
  as `/assets/*`, are served before rewrites apply.
- `ignoreCommand` (`git diff --quiet HEAD^ HEAD -- . ':!specs' ':!*.md'`) skips the build
  for commits that change only `specs/` or Markdown files.

### Headers

| Path | Headers |
|---|---|
| everything | `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `X-Frame-Options: DENY` |
| `/assets/*` | `Cache-Control: public, max-age=31536000, immutable` (hashed filenames) |
| `/` and `/index.html` | `Cache-Control: public, max-age=0, must-revalidate` |
| `/api/*` | `Cache-Control: no-store` |

### Checking a deployment

```sh
curl https://<deployment>/api/v1/health      # JSON with status ok and the version
curl -I https://<deployment>/                 # headers above
cd apps/api && BASE_URL=https://<deployment> uv run pytest -m integration -o addopts=""
```

Open the root URL, enter a name and press "Ping API" to see the greeting. A client-side
path such as `/anything` should return the app, while `/api/nope` returns a JSON 404
envelope.

## CI (GitHub Actions)

`.github/workflows/ci.yml` runs on pull requests and on pushes to `main`. Permissions are
read-only, a newer push to the same ref cancels the older run, and every job has a
15-minute timeout. Actions are pinned by version tag; Dependabot (`.github/dependabot.yml`)
proposes weekly updates for the API (`uv`), web (`npm`) and the actions themselves.

| Job | Runs when | What it does |
|---|---|---|
| `changes` | always | Detects which parts changed (path filter). `api` = `apps/api/**`, `api/**`, `vercel.json`, the workflow file. `web` = `apps/web/**`, the workflow file. |
| `api` | api changed | `uv sync --frozen`, ruff check, ruff format check, ty, pytest with the 90% coverage gate, `uv lock --check`, and a check that `requirements.txt` matches the lockfile export |
| `web` | web changed | `npm ci`, lint, format check, typecheck, tests with coverage, build (includes the bundle size check, 150 KB gzipped) |
| `e2e` | api or web changed | Installs both parts and Chromium, runs `npm run e2e` |
| `ci-ok` | always | Aggregate gate: fails if any job failed or was cancelled; skipped jobs count as passing |

Because path-skipped jobs report "skipped" and `ci-ok` accepts that, a Markdown-only PR
still gets a green required check.

### Branch protection

In the GitHub repository: Settings -> Branches (or Rulesets) -> add a rule for `main`:

1. Require a pull request before merging.
2. Require status checks to pass, and add **exactly one** required check: `ci-ok`. Do
   not require `api`, `web` or `e2e` individually, since those are skipped when
   irrelevant and would block merges.
3. Optionally require branches to be up to date.

Adding a job to the workflow: give it `timeout-minutes: 15`, add it to `needs` of
`ci-ok`, and update the expected job list in `apps/api/tests/unit/test_ci_config.py`
(which also checks permissions, concurrency, action pinning, path filters and that no
workflow mentions `VERCEL_`).

## Environments

| Environment | Where | `APP_ENV` | How the web is served |
|---|---|---|---|
| Local, two servers | your machine | `local` (default) | Vite dev server with `/api` proxy |
| Local, single process | your machine | `local` | FastAPI with `WEB_DIST_DIR` |
| Preview | Vercel, per pull request | `preview` | Vercel CDN + Python function |
| Production | Vercel, `main` | `production` | Vercel CDN + Python function |

`APP_ENV` shows up as `env` in every log line.

## Troubleshooting

- **`ModuleNotFoundError: canasta_api` on Vercel**: the sources were not shipped. Check
  `functions."api/index.py".includeFiles` in `vercel.json` and that the shim `api/index.py`
  still inserts `apps/api/src` into `sys.path`.
- **Build fails installing the editable project or a `file://` path**: `requirements.txt`
  must be exported with `--no-emit-project`. The package is not installed on Vercel; the
  shim adds its source folder instead.
- **Health reports the wrong version or crashes reading metadata**: the version must come
  from `canasta_api.__version__`, never `importlib.metadata`, and equal `pyproject.toml`'s
  `[project].version`.
- **CI "requirements.txt matches the lockfile" fails**: regenerate it (see
  getting-started) and commit.
- **`/api/...` returns the web app or 404 HTML on Vercel**: the Root Directory is not the
  repository root, or `vercel.json` was not picked up.
- **Static files served by the function**: `WEB_DIST_DIR` must not be set on Vercel.
- **A change was not deployed**: `ignoreCommand` skips commits that touch only `specs/`
  or `*.md` files.
- **Merge blocked on a missing check**: branch protection requires something other than
  `ci-ok`, or the workflow did not run; see the branch-protection section.

Unverified parts of this setup are listed in [limitations](limitations.md).
