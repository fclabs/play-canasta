"""Application factory."""

from __future__ import annotations

from fastapi import FastAPI

from canasta_api import __version__
from canasta_api.routers import health, hello
from canasta_api.settings import API_PREFIX, SERVICE_NAME, Settings


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
    app.include_router(health.router)
    app.include_router(hello.router)
    return app


app = create_app()
