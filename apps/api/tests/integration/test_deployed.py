"""Smoke checks against a deployed Canasta (Vercel preview or production)."""

from __future__ import annotations

import os

import httpx
import pytest

pytestmark = pytest.mark.integration

BASE_URL = os.environ.get("BASE_URL")
requires_base_url = pytest.mark.skipif(not BASE_URL, reason="BASE_URL not set")


def _url(path: str) -> str:
    assert BASE_URL is not None
    return f"{BASE_URL.rstrip('/')}{path}"


@requires_base_url
def test_deployed_health_is_ok():
    """
    Given a deployed Canasta service at BASE_URL,
    When its health endpoint is requested,
    Then it reports status ok.
    """
    # When
    response = httpx.get(_url("/api/v1/health"), timeout=10)

    # Then
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@requires_base_url
def test_deployed_home_page_welcomes_visitors():
    """
    Given a deployed Canasta service at BASE_URL,
    When the home page is requested,
    Then it is HTML containing "Welcome to Canasta".
    """
    # When
    response = httpx.get(_url("/"), timeout=10, follow_redirects=True)

    # Then
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Welcome to Canasta" in response.text
