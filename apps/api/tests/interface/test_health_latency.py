from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.interface

CALLS = 100
P95_BUDGET_MS = 50.0


def test_health_p95_latency_is_within_budget(client: TestClient):
    # Given a warm app (NFR-004)
    client.get("/api/v1/health")

    # When 100 sequential requests are timed
    samples: list[float] = []
    for _ in range(CALLS):
        start = time.perf_counter()
        response = client.get("/api/v1/health")
        samples.append((time.perf_counter() - start) * 1000)
        assert response.status_code == 200

    # Then p95 <= 50 ms
    p95 = sorted(samples)[int(CALLS * 0.95) - 1]
    assert p95 <= P95_BUDGET_MS
