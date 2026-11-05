"""Tests for security finding models."""

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from jc_github_action_security_auditor.models import Finding, Severity


def test_finding_fields() -> None:
    path = Path(".github/workflows/ci.yml")
    finding = Finding("RULE-1", Severity.HIGH, "Example", path, 12, "Fix it")

    assert finding.rule_id == "RULE-1"
    assert finding.severity is Severity.HIGH
    assert finding.message == "Example"
    assert finding.file_path == path
    assert finding.line == 12
    assert finding.recommendation == "Fix it"


def test_optional_fields_default_to_none() -> None:
    finding = Finding("RULE-1", Severity.LOW, "Example", Path("ci.yml"))
    assert finding.line is None
    assert finding.recommendation is None


def test_finding_is_immutable() -> None:
    finding = Finding("RULE-1", Severity.LOW, "Example", Path("ci.yml"))
    with pytest.raises(FrozenInstanceError):
        finding.message = "Changed"


def test_severity_values() -> None:
    assert {severity.value for severity in Severity} == {
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL",
    }
