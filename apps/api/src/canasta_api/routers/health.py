"""Health router."""

from __future__ import annotations

from fastapi import APIRouter

from canasta_api import __version__
from canasta_api.schemas.health import HealthResponse
from canasta_api.settings import API_V1_PREFIX, SERVICE_NAME

router = APIRouter(prefix=API_V1_PREFIX, tags=["health"])


@router.get("/health")
def get_health() -> HealthResponse:
    return HealthResponse(status="ok", service=SERVICE_NAME, version=__version__)
