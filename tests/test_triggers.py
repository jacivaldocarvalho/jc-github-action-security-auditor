"""Tests for privileged workflow trigger detection."""

from pathlib import Path

import pytest

from jc_github_action_security_auditor.models import Severity
from jc_github_action_security_auditor.parser import parse_workflow
from jc_github_action_security_auditor.rules.triggers import detect_privileged_triggers


@pytest.mark.parametrize(
    ("trigger", "rule_ids"),
    [
        ("pull_request_target", ["GHA001"]),
        ("workflow_run", ["GHA002"]),
        (["workflow_run", "pull_request_target"], ["GHA001", "GHA002"]),
        ({"pull_request_target": {}, "workflow_run": {}}, ["GHA001", "GHA002"]),
        (["push", "pull_request"], []),
        (["workflow_run", "workflow_run"], ["GHA002"]),
        ([None, {}, "pull_request_target"], ["GHA001"]),
        (None, []),
        (42, []),
        ({"push": {}}, []),
    ],
)
def test_trigger_formats(trigger: object, rule_ids: list[str]) -> None:
    path = Path(".github/workflows/ci.yml")
    findings = detect_privileged_triggers({"on": trigger}, path)
    assert [finding.rule_id for finding in findings] == rule_ids
    for finding in findings:
        assert finding.severity is Severity.MEDIUM
        assert finding.file_path == path
        assert finding.message
        assert finding.recommendation
        assert finding.line is None


def test_missing_trigger() -> None:
    assert detect_privileged_triggers({}, Path("ci.yml")) == []


def test_parsed_workflow(tmp_path: Path) -> None:
    path = tmp_path / "ci.yml"
    path.write_text("on: [push, pull_request_target, workflow_run]\n", encoding="utf-8")
    findings = detect_privileged_triggers(parse_workflow(path), path)
    assert [finding.rule_id for finding in findings] == ["GHA001", "GHA002"]
