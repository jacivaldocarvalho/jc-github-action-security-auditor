"""Identify explicit token permissions that warrant review."""

from pathlib import Path

from jc_github_action_security_auditor.models import Finding, Severity


def _check_permissions(value: object, scope: str, path: Path) -> list[Finding]:
    if value == "write-all":
        return [
            Finding(
                rule_id="GHA003",
                severity=Severity.HIGH,
                message=f"{scope} declares write-all token permissions.",
                file_path=path,
                recommendation=(
                    "Replace write-all with only the permissions required by this "
                    "workflow or job, following least privilege."
                ),
            )
        ]
    if isinstance(value, dict):
        write_scopes = sorted(
            key
            for key, permission in value.items()
            if isinstance(key, str) and permission == "write"
        )
        if write_scopes:
            return [
                Finding(
                    rule_id="GHA004",
                    severity=Severity.MEDIUM,
                    message=f"{scope} declares write permissions for: {', '.join(write_scopes)}; review required.",
                    file_path=path,
                    recommendation=(
                        "Review each write permission and grant only the access "
                        "required by this workflow or job."
                    ),
                )
            ]
    return []


def detect_token_permissions(workflow: dict[str, object], path: Path) -> list[Finding]:
    """Return findings for explicit workflow and job token permissions."""
    findings = _check_permissions(workflow.get("permissions"), "Workflow", path)
    jobs = workflow.get("jobs")
    if isinstance(jobs, dict):
        for job_id, job in jobs.items():
            if isinstance(job_id, str) and isinstance(job, dict):
                findings.extend(
                    _check_permissions(job.get("permissions"), f"Job '{job_id}'", path)
                )
    return findings
