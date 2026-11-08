from __future__ import annotations

import os

import httpx
import pytest

pytestmark = pytest.mark.integration

BASE_URL = os.environ.get("BASE_URL")


@pytest.mark.skipif(not BASE_URL, reason="BASE_URL not set")
def test_deployed_health_is_ok():
    """
    Given a deployed Canasta service at BASE_URL,
    When its health endpoint is requested,
    Then it reports status ok.
    """
    assert BASE_URL is not None
    response = httpx.get(f"{BASE_URL.rstrip('/')}/api/v1/health", timeout=10)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
