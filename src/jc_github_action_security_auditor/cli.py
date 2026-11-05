"""Command-line interface for the auditor."""

import argparse
import sys
from dataclasses import replace
from importlib.metadata import version
from pathlib import Path

from jc_github_action_security_auditor.config import (
    ConfigError,
    RuleConfig,
    load_config,
)
from jc_github_action_security_auditor.discovery import discover_workflows
from jc_github_action_security_auditor.models import Finding
from jc_github_action_security_auditor.parser import WorkflowParseError, parse_workflow
from jc_github_action_security_auditor.reporting import (
    ScanResult,
    WorkflowError,
    to_json,
    to_markdown,
)
from jc_github_action_security_auditor.rules.action_pinning import (
    detect_unpinned_actions,
    detect_unpinned_reusable_workflows,
)
from jc_github_action_security_auditor.rules.permissions import detect_token_permissions
from jc_github_action_security_auditor.rules.triggers import detect_privileged_triggers


def main() -> int:
    """Run the command-line interface."""
    parser = argparse.ArgumentParser(description="Audit GitHub Actions workflows.")
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {version('jc-github-action-security-auditor')}",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    scan_parser = subparsers.add_parser("scan", help="Discover and analyze workflows.")
    scan_parser.add_argument("repository", type=Path, help="Path to the repository.")
    scan_parser.add_argument(
        "--config", type=Path, help="Path to a YAML configuration file."
    )
    scan_parser.add_argument(
        "--format",
        choices=("text", "json", "markdown"),
        default="text",
        help="Report format (default: text).",
    )
    args = parser.parse_args()

    if args.command == "scan":
        try:
            config = (
                load_config(args.config) if args.config is not None else RuleConfig()
            )
        except ConfigError as error:
            print(f"Error loading configuration: {error}", file=sys.stderr)
            return 1
        try:
            workflows = discover_workflows(args.repository)
        except (OSError, ValueError) as error:
            print(f"Error discovering workflows: {error}", file=sys.stderr)
            return 1
        if workflows:
            errors: list[WorkflowError] = []
            analyzed = 0
            findings: list[Finding] = []
            for workflow in workflows:
                try:
                    data = parse_workflow(workflow)
                except WorkflowParseError as error:
                    errors.append(
                        WorkflowError(workflow.relative_to(args.repository), str(error))
                    )
                    if args.format == "text":
                        print(f"ERROR {error}", file=sys.stderr)
                else:
                    analyzed += 1
                    if args.format == "text":
                        print(f"OK {workflow.relative_to(args.repository)}")
                    if config.enabled_rules & {"GHA001", "GHA002"}:
                        findings.extend(
                            detect_privileged_triggers(
                                data, workflow, enabled_rules=config.enabled_rules
                            )
                        )
                    if config.enabled_rules & {"GHA003", "GHA004"}:
                        findings.extend(
                            detect_token_permissions(
                                data, workflow, enabled_rules=config.enabled_rules
                            )
                        )
                    if config.is_enabled("GHA005"):
                        findings.extend(detect_unpinned_actions(data, workflow))
                    if config.is_enabled("GHA006"):
                        findings.extend(
                            detect_unpinned_reusable_workflows(data, workflow)
                        )
            ordered = sorted(findings, key=lambda item: (item.file_path, item.rule_id))
            result = ScanResult(
                tuple(
                    replace(
                        finding,
                        file_path=finding.file_path.relative_to(args.repository),
                    )
                    for finding in ordered
                ),
                tuple(errors),
                analyzed,
            )
        else:
            result = ScanResult()
            if args.format == "text":
                print("No workflow files found.")
        if args.format == "json":
            print(to_json(result))
        elif args.format == "markdown":
            print(to_markdown(result), end="")
        else:
            for finding in result.findings:
                print(
                    f"{finding.rule_id} {finding.severity.value} {finding.file_path}: {finding.message}"
                )
                if finding.recommendation:
                    print(f"  Recommendation: {finding.recommendation}")
        return int(result.has_issues)
    return 0


if __name__ == "__main__":
    sys.exit(main())
