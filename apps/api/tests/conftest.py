"""Shared fixtures."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

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


@pytest.fixture
def log_lines(capsys: pytest.CaptureFixture[str]) -> Callable[[], list[dict[str, Any]]]:
    """Return a callable that drains stdout and parses each line as JSON.

    Each call returns only the lines emitted since the previous call.
    """

    def read() -> list[dict[str, Any]]:
        out = capsys.readouterr().out
        return [json.loads(line) for line in out.splitlines() if line.strip()]

    return read
