"""unit-layer fixtures: deterministic clock, timer and uuid factory."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

import pytest

FIXED_NOW = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)


@pytest.fixture
def fixed_clock() -> Callable[[], datetime]:
    return lambda: FIXED_NOW


@pytest.fixture
def fake_timer() -> Callable[[], float]:
    """Timer advancing 0.0123s per call: latency becomes 12.3 ms."""
    ticks = iter(i * 0.0123 for i in range(100))
    return lambda: next(ticks)


@pytest.fixture
def fixed_uuid() -> Callable[[], str]:
    return lambda: "00000000-0000-4000-8000-000000000000"
