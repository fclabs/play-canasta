.PHONY: install dev-api dev-web test lint

install:
	cd apps/api && uv sync --frozen
	cd apps/web && npm ci

dev-api:
	cd apps/api && uv run uvicorn canasta_api.main:app --reload

dev-web:
	cd apps/web && npm run dev

# Run both parts even if the first fails; exit non-zero if either failed.
test:
	@status=0; \
	(cd apps/api && uv run pytest) || status=1; \
	(cd apps/web && npm test) || status=1; \
	exit $$status

lint:
	@status=0; \
	(cd apps/api && uv run ruff check . && uv run ruff format --check . && uv run ty check) || status=1; \
	(cd apps/web && npm run lint && npm run format:check && npm run typecheck) || status=1; \
	exit $$status
