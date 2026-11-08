# Overview

## What this is

Canasta will be a browser game: one human and one AI partner play against two AI
opponents. The backend is Python/FastAPI and the client is TypeScript/React. The AI
decision logic is meant to stay separate from the game engine.

This repository is the foundation for that work. It does not contain any Canasta rules,
cards, scoring or AI yet. It contains everything needed to add them safely: two
independently built and tested parts, CI that gates merges, and a deployed end-to-end
slice.

## What is in it

- **API** (`apps/api`): FastAPI app with `GET /api/v1/health` and
  `GET /api/v1/hello?name=`, OpenAPI docs at `/api/docs`, environment-based settings,
  a uniform error envelope, a request ID on every response, and one structured JSON log
  line per request. It can optionally serve the built web app.
- **Web** (`apps/web`): a welcome page. You enter a name, press "Ping API", and it shows
  the API's greeting, with loading and error states. It is accessible (axe-checked) and
  fits a 375 px phone screen.
- **Tests**: pytest in four layers (unit, functional, interface, integration) with
  enforced rules, Vitest component tests, and a Playwright end-to-end smoke test.
- **CI** (GitHub Actions): path-aware jobs for each part plus an end-to-end job, behind a
  single required check named `ci-ok`. Dependabot keeps dependencies current.
- **Deployment** (Vercel): the web bundle goes to the CDN and FastAPI runs as one Python
  function behind `/api/*`, with security and cache headers.

## Why it is built this way

- **Two parts that do not depend on each other.** `apps/web` never imports from
  `apps/api` and vice versa; they meet only through the HTTP contract. Each has its own
  toolchain, lockfile and gates, so CI can skip the part a change did not touch.
- **Everything under `/api`.** One prefix lets the same app run behind the Vite proxy,
  FastAPI static mode and Vercel rewrites without CORS. Domain routes live under
  `/api/v1`, leaving room for a future version.
- **Business logic free of HTTP.** Services do not know about FastAPI, which keeps future
  game logic testable on its own.
- **One way to fail.** Every error response has the same JSON shape and request ID, so
  the client and the logs can rely on it.
- **Reproducible and cheap to start.** Locked dependencies, a short quick start, and
  gates that run the same locally and in CI.

Next: [Getting started](getting-started.md), then [Architecture](architecture.md).
