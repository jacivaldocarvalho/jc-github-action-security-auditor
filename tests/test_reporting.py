"""Tests for structured scan result models."""

import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from jc_github_action_security_auditor.models import Finding, Severity
from jc_github_action_security_auditor.reporting import (
    ScanResult,
    WorkflowError,
    to_json,
    to_markdown,
)


def test_empty_result() -> None:
    result = ScanResult()
    assert result.findings == ()
    assert result.errors == ()
    assert result.analyzed_workflows == 0
    assert result.finding_count == result.error_count == 0
    assert not result.has_issues


def test_mixed_results_preserve_order_and_counts() -> None:
    first = Finding("GHA002", Severity.MEDIUM, "First", Path("b.yml"))
    second = Finding("GHA001", Severity.MEDIUM, "Second", Path("a.yml"))
    error = WorkflowError(Path("bad.yml"), "Invalid YAML")
    result = ScanResult((first, second), (error,), analyzed_workflows=3)
    assert result.findings == (first, second)
    assert result.errors == (error,)
    assert result.finding_count == 2
    assert result.error_count == 1
    assert result.analyzed_workflows == 3
    assert result.has_issues


def test_result_copies_collections_and_is_immutable() -> None:
    findings = [Finding("GHA001", Severity.MEDIUM, "Review", Path("ci.yml"))]
    errors = [WorkflowError(Path("bad.yml"), "Invalid YAML")]
    result = ScanResult(findings, errors, 1)
    findings.clear()
    errors.clear()
    assert result.finding_count == result.error_count == 1
    assert isinstance(result.findings, tuple) and isinstance(result.errors, tuple)
    with pytest.raises(FrozenInstanceError):
        result.analyzed_workflows = 2
    with pytest.raises(FrozenInstanceError):
        result.errors[0].message = "Changed"


@pytest.mark.parametrize("has_finding", [True, False])
def test_findings_or_errors_are_issues(has_finding: bool) -> None:
    finding = Finding("GHA001", Severity.MEDIUM, "Review", Path("ci.yml"))
    error = WorkflowError(Path("bad.yml"), "Invalid YAML")
    result = ScanResult(
        (finding,) if has_finding else (), () if has_finding else (error,)
    )
    assert result.has_issues


def test_json_empty_result() -> None:
    assert json.loads(to_json(ScanResult())) == {
        "summary": {"workflows_analyzed": 0, "findings": 0, "errors": 0},
        "findings": [],
        "errors": [],
    }


def test_json_mixed_results_preserves_fields_order_and_input() -> None:
    first = Finding(
        "GHA005",
        Severity.MEDIUM,
        "Example finding",
        Path(".github/workflows/ci.yml"),
        recommendation="Pin to a full commit SHA.",
    )
    second = Finding("GHA003", Severity.HIGH, "Review", Path("other.yml"), line=12)
    errors = (
        WorkflowError(Path("z.yml"), "Invalid YAML"),
        WorkflowError(Path("a.yml"), "Unreadable"),
    )
    result = ScanResult((first, second), errors, 2)
    serialized = to_json(result)
    assert serialized == to_json(result)
    assert serialized.startswith('{\n  "summary": {')
    data = json.loads(serialized)
    assert list(data) == ["summary", "findings", "errors"]
    assert data["summary"] == {"workflows_analyzed": 2, "findings": 2, "errors": 2}
    assert data["findings"] == [
        {
            "rule_id": "GHA005",
            "severity": "MEDIUM",
            "message": "Example finding",
            "file_path": ".github/workflows/ci.yml",
            "line": None,
            "recommendation": "Pin to a full commit SHA.",
        },
        {
            "rule_id": "GHA003",
            "severity": "HIGH",
            "message": "Review",
            "file_path": "other.yml",
            "line": 12,
            "recommendation": None,
        },
    ]
    assert data["errors"] == [
        {"file_path": "z.yml", "message": "Invalid YAML"},
        {"file_path": "a.yml", "message": "Unreadable"},
    ]
    assert result == ScanResult((first, second), errors, 2)


def test_markdown_empty_report() -> None:
    report = to_markdown(ScanResult())
    assert "# GitHub Actions Security Audit" in report
    assert "Workflows analyzed: 0" in report
    assert "Findings: 0" in report and "Errors: 0" in report
    assert "No findings." in report and "No workflow errors." in report


def test_markdown_mixed_order_optional_fields_and_escaping() -> None:
    first = Finding(
        "GHA005",
        Severity.MEDIUM,
        "[click](https://evil.test)\n<script>alert(1)</script>",
        Path("bad[link].yml"),
        9,
        "Use `sha`\n# injected",
    )
    second = Finding("GHA001", Severity.HIGH, "plain", Path("other.yml"))
    errors = (
        WorkflowError(Path("x|y.yml"), "bad\n## forged"),
        WorkflowError(Path("last.yml"), "oops"),
    )
    result = ScanResult((first, second), errors, 3)
    report = to_markdown(result)
    assert report == to_markdown(result)
    assert "Workflows analyzed: 3" in report
    assert "Findings: 2" in report and "Errors: 2" in report
    assert report.index("GHA005") < report.index("GHA001")
    assert report.index("x\\|y") < report.index("last")
    assert "- Line: 9" in report
    assert report.count("- Recommendation:") == 1
    assert "\\[click\\]\\(https://evil\\.test\\)" in report
    assert "&lt;script&gt;" in report and "<script>" not in report
    assert "\\`sha\\` \\# injected" in report
    assert "bad \\#\\# forged" in report
    assert result == ScanResult((first, second), errors, 3)
