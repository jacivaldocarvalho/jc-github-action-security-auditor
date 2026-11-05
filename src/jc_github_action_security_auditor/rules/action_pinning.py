"""Identify remote actions and reusable workflows without full SHA pins."""

import re
from pathlib import Path

from jc_github_action_security_auditor.models import Finding, Severity


def _is_full_sha(ref: str) -> bool:
    return re.fullmatch(r"[0-9a-fA-F]{40}", ref) is not None


def detect_unpinned_actions(workflow: dict[str, object], path: Path) -> list[Finding]:
    """Return a finding for each unpinned remote action step."""
    jobs = workflow.get("jobs")
    if not isinstance(jobs, dict):
        return []

    findings = []
    for job_id, job in jobs.items():
        if not isinstance(job_id, str) or not isinstance(job, dict):
            continue
        steps = job.get("steps")
        if not isinstance(steps, list):
            continue
        for index, step in enumerate(steps, start=1):
            if not isinstance(step, dict):
                continue
            uses = step.get("uses")
            if not isinstance(uses, str) or uses.startswith(("./", "docker://")):
                continue
            action, separator, ref = uses.rpartition("@")
            parts = action.split("/")
            if not separator or not ref or len(parts) < 2 or not all(parts):
                continue
            if _is_full_sha(ref):
                continue
            findings.append(
                Finding(
                    rule_id="GHA005",
                    severity=Severity.MEDIUM,
                    message=f"Job '{job_id}', step {index} uses an unpinned remote action: {uses}.",
                    file_path=path,
                    recommendation="Pin the action to a reviewed full 40-character commit SHA.",
                )
            )
    return findings


def detect_unpinned_reusable_workflows(
    workflow: dict[str, object], path: Path
) -> list[Finding]:
    """Return a finding for each unpinned remote reusable workflow job."""
    jobs = workflow.get("jobs")
    if not isinstance(jobs, dict):
        return []

    findings = []
    for job_id, job in jobs.items():
        if not isinstance(job_id, str) or not isinstance(job, dict):
            continue
        uses = job.get("uses")
        if not isinstance(uses, str) or uses.startswith("./"):
            continue
        target, separator, ref = uses.rpartition("@")
        parts = target.split("/")
        if (
            not separator
            or not ref
            or len(parts) != 5
            or not all(parts)
            or parts[2:4] != [".github", "workflows"]
            or not parts[4].endswith((".yml", ".yaml"))
            or _is_full_sha(ref)
        ):
            continue
        findings.append(
            Finding(
                rule_id="GHA006",
                severity=Severity.MEDIUM,
                message=f"Job '{job_id}' uses an unpinned remote reusable workflow: {uses}.",
                file_path=path,
                recommendation=(
                    "Pin the reusable workflow to a reviewed full 40-character commit SHA."
                ),
            )
        )
    return findings
