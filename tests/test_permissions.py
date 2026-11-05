"""Tests for explicit token permission analysis."""

from pathlib import Path

import pytest

from jc_github_action_security_auditor.models import Severity
from jc_github_action_security_auditor.parser import parse_workflow
from jc_github_action_security_auditor.rules.permissions import detect_token_permissions


def test_workflow_write_all() -> None:
    path = Path("ci.yml")
    findings = detect_token_permissions({"permissions": "write-all"}, path)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.rule_id == "GHA003"
    assert finding.severity is Severity.HIGH
    assert finding.file_path == path
    assert "Workflow" in finding.message
    assert "least privilege" in finding.recommendation


def test_job_write_all() -> None:
    findings = detect_token_permissions(
        {"jobs": {"deploy": {"permissions": "write-all"}}}, Path("ci.yml")
    )
    assert len(findings) == 1
    assert findings[0].rule_id == "GHA003"
    assert findings[0].severity is Severity.HIGH
    assert "deploy" in findings[0].message


def test_multiple_writes_in_one_declaration() -> None:
    findings = detect_token_permissions(
        {
            "permissions": {
                "pull-requests": "write",
                "contents": "write",
                "actions": "read",
            }
        },
        Path("ci.yml"),
    )
    assert len(findings) == 1
    assert findings[0].rule_id == "GHA004"
    assert findings[0].severity is Severity.MEDIUM
    assert "Workflow" in findings[0].message
    assert "contents, pull-requests" in findings[0].message
    assert findings[0].recommendation


def test_inheritance_and_job_overrides() -> None:
    workflow = {
        "permissions": {"contents": "write"},
        "jobs": {
            "inherits": {"steps": []},
            "readonly": {"permissions": "read-all"},
            "override": {"permissions": {"pull-requests": "write"}},
            "full": {"permissions": "write-all"},
        },
    }
    findings = detect_token_permissions(workflow, Path("ci.yml"))
    assert [finding.rule_id for finding in findings] == ["GHA004", "GHA004", "GHA003"]
    assert "Workflow" in findings[0].message
    assert "override" in findings[1].message
    assert "pull-requests" in findings[1].message
    assert "full" in findings[2].message


@pytest.mark.parametrize(
    "permissions",
    [None, "read-all", {}, {"contents": "read"}, [], 42, {"contents": []}],
)
def test_no_finding_for_read_only_missing_or_malformed(permissions: object) -> None:
    assert detect_token_permissions({"permissions": permissions}, Path("ci.yml")) == []


@pytest.mark.parametrize("jobs", [None, [], "invalid", {"bad": None}, {"bad": []}])
def test_malformed_jobs(jobs: object) -> None:
    assert detect_token_permissions({"jobs": jobs}, Path("ci.yml")) == []


def test_parser_integration(tmp_path: Path) -> None:
    path = tmp_path / "ci.yml"
    path.write_text(
        "jobs:\n  build:\n    permissions:\n      contents: write\n", encoding="utf-8"
    )
    findings = detect_token_permissions(parse_workflow(path), path)
    assert len(findings) == 1
    assert findings[0].rule_id == "GHA004"
    assert findings[0].file_path == path
