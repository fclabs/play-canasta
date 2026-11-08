"""Error envelope schema (FR-014)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str
    details: list[dict[str, Any]] | None = None


class ErrorEnvelope(BaseModel):
    """Body of every non-2xx response: ``{"error": {...}}``."""

    error: ErrorBody
