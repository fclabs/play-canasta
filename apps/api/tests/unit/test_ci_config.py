from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[4]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
CI_PATH = WORKFLOWS / "ci.yml"
CI: dict[str, Any] = yaml.safe_load(CI_PATH.read_text(encoding="utf-8"))
DEPENDABOT: dict[str, Any] = yaml.safe_load(
    (REPO_ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
)
JOBS: dict[str, Any] = CI["jobs"]


def _uses_refs() -> list[str]:
    return [
        step["uses"]
        for job in JOBS.values()
        for step in job.get("steps", [])
        if "uses" in step
    ]


def test_workflow_has_the_expected_jobs():
    # Given the CI workflow
    # When listing its jobs
    # Then they are exactly the five named in the spec
    assert set(JOBS) == {"changes", "api", "web", "e2e", "ci-ok"}


def test_workflow_token_is_read_only():
    # Given the CI workflow
    # When reading top-level permissions
    # Then only contents: read is granted
    assert CI["permissions"] == {"contents": "read"}


def test_superseded_runs_are_cancelled_per_ref():
    # Given the CI workflow
    # When reading concurrency
    # Then the group is per ref and in-progress runs are cancelled
    concurrency = CI["concurrency"]
    assert concurrency["cancel-in-progress"] is True
    assert "github.ref" in concurrency["group"]


def test_every_job_has_a_15_minute_timeout():
    # Given the CI workflow
    # When reading each job
    # Then each declares timeout-minutes: 15
    assert {name: job.get("timeout-minutes") for name, job in JOBS.items()} == {
        name: 15 for name in JOBS
    }


def test_actions_are_pinned_not_floating():
    # Given every `uses:` reference
    refs = _uses_refs()
    # When checking the ref after "@"
    # Then none is main/master and each is a version tag or a full SHA
    assert refs
    for ref in refs:
        _, _, version = ref.partition("@")
        assert version not in {"", "main", "master"}, ref
        assert re.fullmatch(r"v\d+(\.\d+){0,2}|[0-9a-f]{40}", version), ref


def test_ci_ok_aggregates_all_jobs_even_when_they_fail():
    # Given the ci-ok job
    ci_ok = JOBS["ci-ok"]
    # When reading its wiring
    # Then it needs every other job and always runs
    assert ci_ok["needs"] == ["changes", "api", "web", "e2e"]
    assert ci_ok["if"] == "always()"


def test_path_filter_routes_parts_and_workflow_changes():
    # Given the paths-filter step of the changes job
    step = next(s for s in JOBS["changes"]["steps"] if s.get("id") == "filter")
    filters = yaml.safe_load(step["with"]["filters"])
    # When reading the filters
    # Then api/web paths map to their part and the workflow file triggers both
    assert {"apps/api/**", "api/**", "vercel.json"} <= set(filters["api"])
    assert "apps/web/**" in filters["web"]
    assert ".github/workflows/ci.yml" in filters["api"]
    assert ".github/workflows/ci.yml" in filters["web"]


def test_e2e_runs_when_either_part_changed():
    # Given the e2e job condition
    condition = JOBS["e2e"]["if"]
    # When reading it
    # Then it references both path outputs
    assert "outputs.api" in condition
    assert "outputs.web" in condition


def test_dependabot_updates_each_ecosystem_weekly():
    # Given the dependabot config
    updates = {u["package-ecosystem"]: u for u in DEPENDABOT["updates"]}
    # When reading ecosystems
    # Then uv, npm and github-actions are weekly with the right directory
    assert set(updates) == {"uv", "npm", "github-actions"}
    assert updates["uv"]["directory"] == "/apps/api"
    assert updates["npm"]["directory"] == "/apps/web"
    assert updates["github-actions"]["directory"] == "/"
    assert all(u["schedule"]["interval"] == "weekly" for u in updates.values())


def test_no_workflow_references_vercel_secrets_or_tokens():
    # Given every workflow file
    files = [*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml")]
    # When scanning for VERCEL_ strings
    # Then none is found (deployment is Vercel's Git integration, BR-006)
    assert files
    assert [f.name for f in files if "VERCEL_" in f.read_text(encoding="utf-8")] == []
