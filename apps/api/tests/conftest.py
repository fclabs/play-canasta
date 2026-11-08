"""Shared fixtures."""

from __future__ import annotations

import pytest
from fastapi import FastAPI

from canasta_api.main import create_app
from canasta_api.settings import Settings


@pytest.fixture
def settings() -> Settings:
    """Settings injected explicitly; ignores any local .env file."""
    return Settings(_env_file=None)


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)
