"""Tests for remote action pinning detection."""

from pathlib import Path

import pytest

from jc_github_action_security_auditor.models import Severity
from jc_github_action_security_auditor.parser import parse_workflow
from jc_github_action_security_auditor.rules.action_pinning import (
    detect_unpinned_actions,
    detect_unpinned_reusable_workflows,
)


@pytest.mark.parametrize(
    "uses", ["actions/checkout@v4", "owner/repo@main", "owner/repo/path@abc1234"]
)
def test_unpinned_remote_actions(uses: str) -> None:
    path = Path("ci.yml")
    findings = detect_unpinned_actions(
        {"jobs": {"build": {"steps": [{"uses": uses}]}}}, path
    )
    assert len(findings) == 1
    finding = findings[0]
    assert finding.rule_id == "GHA005"
    assert finding.severity is Severity.MEDIUM
    assert finding.file_path == path
    assert "build" in finding.message and "step 1" in finding.message
    assert uses in finding.message
    assert finding.recommendation and "reviewed full" in finding.recommendation


@pytest.mark.parametrize(
    "uses",
    [
        "owner/repo@" + "a" * 40,
        "owner/repo/path@" + "ABCDEF0123" * 4,
        "./local",
        "docker://alpine:latest",
    ],
)
def test_excluded_and_pinned_actions(uses: str) -> None:
    assert (
        detect_unpinned_actions(
            {"jobs": {"build": {"steps": [{"uses": uses}]}}}, Path("ci.yml")
        )
        == []
    )


def test_multiple_jobs_and_steps() -> None:
    workflow = {
        "jobs": {
            "first": {
                "steps": [{"run": "true"}, {"uses": "a/b@main"}, {"uses": "a/b@v1"}]
            },
            "second": {"steps": [{"uses": "c/d@v2"}]},
        }
    }
    findings = detect_unpinned_actions(workflow, Path("ci.yml"))
    assert len(findings) == 3
    assert "first'" in findings[0].message and "step 2" in findings[0].message
    assert "step 3" in findings[1].message
    assert "second'" in findings[2].message and "step 1" in findings[2].message


@pytest.mark.parametrize(
    "workflow",
    [
        {},
        {"jobs": []},
        {"jobs": {"a": None}},
        {"jobs": {"a": {"steps": "bad"}}},
        {
            "jobs": {
                "a": {"steps": [None, {"uses": 42}, {"uses": "a/b"}, {"uses": "a/b@"}]}
            }
        },
        {"jobs": {"reusable": {"uses": "owner/repo/.github/workflows/ci.yml@main"}}},
    ],
)
def test_malformed_and_reusable_workflows(workflow: dict[str, object]) -> None:
    assert detect_unpinned_actions(workflow, Path("ci.yml")) == []


def test_parsed_workflow(tmp_path: Path) -> None:
    path = tmp_path / "ci.yml"
    path.write_text(
        "jobs:\n  build:\n    steps:\n      - uses: actions/checkout@v4\n",
        encoding="utf-8",
    )
    assert len(detect_unpinned_actions(parse_workflow(path), path)) == 1


@pytest.mark.parametrize("ref", ["main", "v1", "abc1234"])
def test_unpinned_reusable_workflow(ref: str) -> None:
    path = Path("ci.yml")
    uses = f"owner/repo/.github/workflows/build.yml@{ref}"
    findings = detect_unpinned_reusable_workflows(
        {"jobs": {"deploy": {"uses": uses}}}, path
    )
    assert len(findings) == 1
    finding = findings[0]
    assert finding.rule_id == "GHA006"
    assert finding.severity is Severity.MEDIUM
    assert finding.file_path == path
    assert "deploy" in finding.message and uses in finding.message
    assert finding.recommendation and "reviewed full" in finding.recommendation


@pytest.mark.parametrize(
    "uses",
    [
        "owner/repo/.github/workflows/build.yml@" + "a" * 40,
        "owner/repo/.github/workflows/build.yaml@" + "ABCDEF0123" * 4,
        "./.github/workflows/build.yml",
        "owner/repo/.github/workflows/build.yml@",
        "owner/repo@main",
        42,
        None,
    ],
)
def test_reusable_excluded_or_malformed(uses: object) -> None:
    assert (
        detect_unpinned_reusable_workflows(
            {"jobs": {"build": {"uses": uses}}}, Path("ci.yml")
        )
        == []
    )


@pytest.mark.parametrize("jobs", [None, [], "invalid", {"broken": None}])
def test_malformed_reusable_jobs(jobs: object) -> None:
    assert detect_unpinned_reusable_workflows({"jobs": jobs}, Path("ci.yml")) == []


def test_reusable_workflow_and_action_findings_are_separate() -> None:
    workflow = {
        "jobs": {
            "first": {"uses": "owner/repo/.github/workflows/a.yml@main"},
            "second": {"uses": "owner/repo/.github/workflows/b.yaml@v2"},
            "build": {"steps": [{"uses": "actions/checkout@v4"}]},
        }
    }
    path = Path("ci.yml")
    reusable = detect_unpinned_reusable_workflows(workflow, path)
    actions = detect_unpinned_actions(workflow, path)
    assert [finding.rule_id for finding in reusable] == ["GHA006", "GHA006"]
    assert "first" in reusable[0].message and "second" in reusable[1].message
    assert [finding.rule_id for finding in actions] == ["GHA005"]
