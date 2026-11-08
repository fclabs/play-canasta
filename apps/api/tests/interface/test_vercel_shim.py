from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.interface

REPO_ROOT = Path(__file__).resolve().parents[4]
SRC = REPO_ROOT / "apps" / "api" / "src"

SCRIPT = """
import importlib.util, json, sys
from pathlib import Path

src = Path(sys.argv[2]).resolve()
sys.path[:] = [p for p in sys.path if Path(p or ".").resolve() != src]
spec = importlib.util.spec_from_file_location("vercel_shim", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

import canasta_api
from fastapi.testclient import TestClient

body = TestClient(module.app).get("/api/v1/health").json()
print(json.dumps({"file": canasta_api.__file__, "body": body,
                  "version": canasta_api.__version__}))
"""


def test_shim_imports_app_with_only_src_prepended_and_no_web_dist(tmp_path):
    # Given a clean interpreter without apps/api/src on sys.path and no
    # WEB_DIST_DIR, as on Vercel
    env = {k: v for k, v in os.environ.items() if k != "WEB_DIST_DIR"}
    env.pop("PYTHONPATH", None)

    # When loading api/index.py and calling health
    result = subprocess.run(
        [sys.executable, "-c", SCRIPT, str(REPO_ROOT / "api" / "index.py"), str(SRC)],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env=env,
        check=False,
    )

    # Then the app imports from apps/api/src and health reports __version__
    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout.strip().splitlines()[-1])
    assert Path(out["file"]).resolve().is_relative_to(SRC)
    assert out["body"]["status"] == "ok"
    assert out["body"]["version"] == out["version"]
