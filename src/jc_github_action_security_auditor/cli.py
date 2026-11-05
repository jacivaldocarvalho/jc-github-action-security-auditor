"""Command-line interface for the auditor."""

import argparse
import sys
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
            failed = False
            findings: list[Finding] = []
            for workflow in workflows:
                try:
                    data = parse_workflow(workflow)
                except WorkflowParseError as error:
                    print(f"ERROR {error}", file=sys.stderr)
                    failed = True
                else:
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
            for finding in sorted(
                findings, key=lambda item: (item.file_path, item.rule_id)
            ):
                path = finding.file_path.relative_to(args.repository)
                print(
                    f"{finding.rule_id} {finding.severity.value} {path}: {finding.message}"
                )
                if finding.recommendation:
                    print(f"  Recommendation: {finding.recommendation}")
            return int(failed or bool(findings))
        else:
            print("No workflow files found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
