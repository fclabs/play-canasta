"""Optional static hosting of a built web bundle (FR-018).

Enabled only when ``WEB_DIST_DIR`` points to a directory containing
``index.html``. Registers one catch-all GET route (hidden from OpenAPI) that
must be added AFTER every API route; ``/api`` paths are never served from disk.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from canasta_api.settings import API_PREFIX

INDEX_FILE = "index.html"


def is_servable_dist(dist_dir: Path | None) -> bool:
    """True when ``dist_dir`` is an existing directory holding ``index.html``."""
    return dist_dir is not None and (dist_dir / INDEX_FILE).is_file()


def is_api_path(path: str) -> bool:
    """True for ``/api`` itself and anything below it."""
    return path == API_PREFIX or path.startswith(f"{API_PREFIX}/")


def resolve_asset(dist_dir: Path, relative: str) -> Path | None:
    """Return the file for ``relative`` inside ``dist_dir``, or None.

    None for anything that is not a regular file strictly inside the (resolved)
    dist directory: missing, directories, traversal, symlinks pointing outside,
    or unresolvable paths.
    """
    root = dist_dir.resolve()
    try:
        candidate = (root / relative).resolve()
    except (OSError, ValueError):
        return None
    if candidate.is_relative_to(root) and candidate.is_file():
        return candidate
    return None


def mount_static(app: FastAPI, dist_dir: Path) -> None:
    """Serve files from ``dist_dir`` with SPA fallback to ``index.html``."""
    root = dist_dir.resolve()

    def serve(full_path: str) -> FileResponse:
        if is_api_path(f"/{full_path}"):
            # Keep the FR-014 envelope for unknown API paths.
            raise StarletteHTTPException(status_code=404)
        asset = resolve_asset(root, full_path)
        return FileResponse(asset if asset is not None else root / INDEX_FILE)

    app.add_api_route(
        "/{full_path:path}", serve, methods=["GET"], include_in_schema=False
    )
