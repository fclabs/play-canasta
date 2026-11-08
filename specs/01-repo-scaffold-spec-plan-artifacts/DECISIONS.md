# DECISIONS

## D-001: Name validation via AfterValidator, not a regex (Iteration 1)
Context: FR-012 allows `str.isalpha()` letters and `str.isdecimal()` digits; Unicode-aware regex classes (`\w`, Rust regex used by pydantic `pattern`) differ (underscore, `isnumeric` chars such as "²").
Decision: `Query(min_length=1, max_length=40)` plus `AfterValidator(validate_name)` in `schemas/hello.py`, implementing the exact char rules and the not-spaces-only rule; no trimming.
Rejected: `pattern=` regex (not equivalent to isalpha/isdecimal; awkward spaces-only rule).
Consequences: Failures surface as FastAPI 422 with field `name` in `loc`; iteration 2 maps them to the envelope.

## D-002: Settings use uppercase validation aliases; injected through create_app (Iteration 1)
Context: FR-017 requires errors naming the env variable; tests must inject settings rather than use globals.
Decision: fields `log_level`, `app_env`, `web_dist_dir` with `validation_alias="LOG_LEVEL"` etc., so error `loc` shows the env name. `create_app(settings: Settings | None = None)`; tests use `Settings(_env_file=None)` and `monkeypatch.setenv`. No module-level `settings` singleton (only the module-level `app`).
Rejected: lowercase field names with case-insensitive env (errors name `log_level`); global singleton.
Consequences: constructing `Settings` directly by kwarg uses aliases (`LOG_LEVEL=...`) or `populate_by_name`.

## D-003: Swagger OAuth2 redirect moved under /api (Iteration 1)
Context: FastAPI registers `/docs/oauth2-redirect` by default, violating BR-002 (all routes under `/api`).
Decision: `swagger_ui_oauth2_redirect_url="/api/docs/oauth2-redirect"`; ReDoc disabled (`redoc_url=None`).
Rejected: disabling the redirect (changes docs behaviour); leaving it (violates BR-002).
Consequences: route-prefix test passes with no exceptions.

## D-004: Constants live in settings.py; build backend hatchling (Iteration 1)
Context: python-coding skill puts `Final` constants beside settings; project must be a uv-installable package under `src/`.
Decision: all shared `Final` constants (prefixes, service name, name limits) in `canasta_api/settings.py`; `[build-system]` hatchling with wheel package `src/canasta_api`; `uv sync` installs editable.
Rejected: separate constants.py (small now); `package = false` (spec/skill expect src layout package).
Consequences: Vercel export must use `--no-emit-project`; `DEFAULT_PLAYER_NAME` alias defined in schemas/hello.py.
