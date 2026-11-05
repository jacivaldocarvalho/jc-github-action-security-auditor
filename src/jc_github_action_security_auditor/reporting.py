"""Immutable scan results and deterministic JSON serialization."""

import json
import re
from dataclasses import dataclass
from html import escape
from pathlib import Path

from jc_github_action_security_auditor.models import Finding


@dataclass(frozen=True)
class WorkflowError:
    """An error encountered while scanning a workflow."""

    file_path: Path
    message: str


@dataclass(frozen=True)
class ScanResult:
    """Findings, errors, and the number of workflows analyzed successfully."""

    findings: tuple[Finding, ...] = ()
    errors: tuple[WorkflowError, ...] = ()
    analyzed_workflows: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "findings", tuple(self.findings))
        object.__setattr__(self, "errors", tuple(self.errors))

    @property
    def finding_count(self) -> int:
        """Return the number of findings."""
        return len(self.findings)

    @property
    def error_count(self) -> int:
        """Return the number of scanning errors."""
        return len(self.errors)

    @property
    def has_issues(self) -> bool:
        """Return whether findings or scanning errors exist."""
        return bool(self.findings or self.errors)


def to_json(result: ScanResult) -> str:
    """Serialize a scan result as human-readable JSON in supplied order."""
    data = {
        "summary": {
            "workflows_analyzed": result.analyzed_workflows,
            "findings": result.finding_count,
            "errors": result.error_count,
        },
        "findings": [
            {
                "rule_id": finding.rule_id,
                "severity": finding.severity.name,
                "message": finding.message,
                "file_path": str(finding.file_path),
                "line": finding.line,
                "recommendation": finding.recommendation,
            }
            for finding in result.findings
        ],
        "errors": [
            {"file_path": str(error.file_path), "message": error.message}
            for error in result.errors
        ],
    }
    return json.dumps(data, indent=2)


def _markdown_text(value: str) -> str:
    """Render untrusted text on one line without Markdown or HTML syntax."""
    text = " ".join(value.split())
    return re.sub(r"([\\`*_{}\[\]()#+.!|~>\-])", r"\\\1", escape(text))


def to_markdown(result: ScanResult) -> str:
    """Render a scan result as a deterministic Markdown report."""
    lines = [
        "# GitHub Actions Security Audit",
        "",
        "## Summary",
        "",
        f"- Workflows analyzed: {result.analyzed_workflows}",
        f"- Findings: {result.finding_count}",
        f"- Errors: {result.error_count}",
        "",
        "## Findings",
        "",
    ]
    if not result.findings:
        lines.extend(["No findings.", ""])
    for finding in result.findings:
        lines.extend(
            [
                f"### {_markdown_text(finding.rule_id)} ({finding.severity.name})",
                "",
                f"- File: {_markdown_text(str(finding.file_path))}",
            ]
        )
        if finding.line is not None:
            lines.append(f"- Line: {finding.line}")
        lines.append(f"- Message: {_markdown_text(finding.message)}")
        if finding.recommendation is not None:
            lines.append(f"- Recommendation: {_markdown_text(finding.recommendation)}")
        lines.append("")
    lines.extend(["## Workflow errors", ""])
    if not result.errors:
        lines.extend(["No workflow errors.", ""])
    for error in result.errors:
        lines.append(
            f"- File: {_markdown_text(str(error.file_path))}; "
            f"error: {_markdown_text(error.message)}"
        )
    return "\n".join(lines) + "\n"
