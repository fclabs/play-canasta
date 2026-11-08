from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[4]
CONFIG: dict[str, Any] = json.loads(
    (REPO_ROOT / "vercel.json").read_text(encoding="utf-8")
)


def _headers_for(source: str) -> dict[str, str]:
    return {
        h["key"]: h["value"]
        for rule in CONFIG["headers"]
        if rule["source"] == source
        for h in rule["headers"]
    }


def test_build_settings_publish_the_web_bundle():
    # Given the Vercel config
    # When reading build settings
    # Then web is installed/built from apps/web and its dist is published
    assert CONFIG["installCommand"] == "npm ci --prefix apps/web"
    assert CONFIG["buildCommand"] == "npm run build --prefix apps/web"
    assert CONFIG["outputDirectory"] == "apps/web/dist"


def test_rewrites_send_api_to_function_before_spa_fallback():
    # Given the Vercel config
    # When reading rewrites
    # Then the order is API first, SPA fallback (excluding /api/) second
    assert CONFIG["rewrites"] == [
        {"source": "/api/(.*)", "destination": "/api/index"},
        {"source": "/((?!api/).*)", "destination": "/index.html"},
    ]


def test_function_bundles_api_sources():
    # Given the Vercel config
    # When reading the function settings
    # Then the python function includes apps/api/src
    assert CONFIG["functions"]["api/index.py"]["includeFiles"] == "apps/api/src/**"


def test_security_headers_apply_to_every_path():
    # Given the Vercel config
    # When reading the catch-all header rule
    # Then the three security headers are present
    assert _headers_for("/(.*)") == {
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "X-Frame-Options": "DENY",
    }


def test_cache_headers_per_path_class():
    # Given the Vercel config
    # When reading cache rules
    # Then assets are immutable, the html entry revalidates, API is no-store
    immutable = "public, max-age=31536000, immutable"
    revalidate = "public, max-age=0, must-revalidate"
    assert _headers_for("/assets/(.*)") == {"Cache-Control": immutable}
    assert _headers_for("/") == {"Cache-Control": revalidate}
    assert _headers_for("/index.html") == {"Cache-Control": revalidate}
    assert _headers_for("/api/(.*)") == {"Cache-Control": "no-store"}


def test_ignore_command_skips_only_specs_and_markdown():
    # Given the Vercel config
    # When reading ignoreCommand
    # Then it is a quiet git diff excluding only specs/** and *.md
    command = CONFIG["ignoreCommand"]
    assert command.startswith("git diff --quiet HEAD^ HEAD")
    assert "':!specs'" in command
    assert "':!*.md'" in command


def test_requirements_file_excludes_the_project_and_dev_tools():
    # Given the exported requirements used by the Vercel function
    text = (REPO_ROOT / "requirements.txt").read_text(encoding="utf-8")
    names = {
        line.split("==")[0]
        for line in text.splitlines()
        if "==" in line and not line.startswith((" ", "#"))
    }

    # Then runtime deps are pinned and the project/dev tools are absent
    assert {"fastapi", "pydantic-settings", "starlette"} <= names
    assert not names & {"canasta-api", "pytest", "ruff", "httpx"}
