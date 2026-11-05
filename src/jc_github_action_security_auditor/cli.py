"""Command-line interface for the auditor."""

import argparse
import sys
from importlib.metadata import version
from pathlib import Path

from jc_github_action_security_auditor.discovery import discover_workflows
from jc_github_action_security_auditor.parser import WorkflowParseError, parse_workflow


def main() -> int:
    """Run the command-line interface."""
    parser = argparse.ArgumentParser(description="Audit GitHub Actions workflows.")
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {version('jc-github-action-security-auditor')}",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    scan_parser = subparsers.add_parser("scan", help="Discover and parse workflows.")
    scan_parser.add_argument("repository", type=Path, help="Path to the repository.")
    args = parser.parse_args()

    if args.command == "scan":
        try:
            workflows = discover_workflows(args.repository)
        except (OSError, ValueError) as error:
            print(f"Error discovering workflows: {error}", file=sys.stderr)
            return 1
        if workflows:
            failed = False
            for workflow in workflows:
                try:
                    parse_workflow(workflow)
                except WorkflowParseError as error:
                    print(f"ERROR {error}", file=sys.stderr)
                    failed = True
                else:
                    print(f"OK {workflow.relative_to(args.repository)}")
            return int(failed)
        else:
            print("No workflow files found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
