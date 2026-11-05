"""Identify workflow triggers that warrant a security review."""

from pathlib import Path

from jc_github_action_security_auditor.models import Finding, Severity


def detect_privileged_triggers(
    workflow: dict[str, object], path: Path
) -> list[Finding]:
    """Return review findings for privileged events in a parsed workflow."""
    triggers = workflow.get("on")
    if isinstance(triggers, str):
        events = {triggers}
    elif isinstance(triggers, (list, dict)):
        events = {event for event in triggers if isinstance(event, str)}
    else:
        return []

    findings = []
    if "pull_request_target" in events:
        findings.append(
            Finding(
                rule_id="GHA001",
                severity=Severity.MEDIUM,
                message="The pull_request_target trigger warrants a security review.",
                file_path=path,
                recommendation=(
                    "Review token permissions and secrets; avoid executing untrusted "
                    "pull request code in a privileged context."
                ),
            )
        )
    if "workflow_run" in events:
        findings.append(
            Finding(
                rule_id="GHA002",
                severity=Severity.MEDIUM,
                message="The workflow_run trigger warrants a security review.",
                file_path=path,
                recommendation=(
                    "Review token permissions and secrets; validate artifacts and "
                    "other inputs from the triggering workflow before using them."
                ),
            )
        )
    return findings
