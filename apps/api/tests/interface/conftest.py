"""interface-layer fixtures."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)
