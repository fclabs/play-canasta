"""Vercel Python function entrypoint: exposes the FastAPI ASGI app as `app`."""

from __future__ import annotations

import sys
from pathlib import Path

# canasta_api is not installed on Vercel (requirements.txt omits the project);
# the sources ship with the function via vercel.json `functions.includeFiles`.
_SRC = str(Path(__file__).resolve().parent.parent / "apps" / "api" / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from canasta_api.main import app  # noqa: E402

__all__ = ["app"]
