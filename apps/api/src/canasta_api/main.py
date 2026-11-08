"""Application factory."""

from __future__ import annotations

from fastapi import FastAPI

from canasta_api import __version__
from canasta_api.errors import register_exception_handlers
from canasta_api.logging import RequestContextMiddleware, configure_logging
from canasta_api.routers import health, hello
from canasta_api.settings import API_PREFIX, SERVICE_NAME, Settings
from canasta_api.static import is_servable_dist, mount_static


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI app. Pass ``settings`` to inject configuration (tests)."""
    resolved = settings if settings is not None else Settings()
    app = FastAPI(
        title=SERVICE_NAME,
        version=__version__,
        docs_url=f"{API_PREFIX}/docs",
        redoc_url=None,
        swagger_ui_oauth2_redirect_url=f"{API_PREFIX}/docs/oauth2-redirect",
        openapi_url=f"{API_PREFIX}/openapi.json",
    )
    app.state.settings = resolved
    configure_logging(resolved.log_level)
    register_exception_handlers(app)
    # Outermost user middleware: covers 404/405/422 and unhandled exceptions.
    app.add_middleware(RequestContextMiddleware, env=resolved.app_env)
    app.include_router(health.router)
    app.include_router(hello.router)
    if resolved.web_dist_dir is not None and is_servable_dist(resolved.web_dist_dir):
        mount_static(app, resolved.web_dist_dir)  # catch-all: must be added last
    return app


app = create_app()
