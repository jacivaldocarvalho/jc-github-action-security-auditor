"""Tests for the public command-line interface."""

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest


def test_help() -> None:
    result = subprocess.run(
        ["jc-gha-audit", "--help"], capture_output=True, text=True, check=False
    )

    assert result.returncode == 0
    assert "scan" in result.stdout
    assert "--version" in result.stdout


def test_version() -> None:
    result = subprocess.run(
        ["jc-gha-audit", "--version"], capture_output=True, text=True, check=False
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "jc-gha-audit 0.1.0"


def test_scan_discovers_workflows(tmp_path: Path) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text("on: push\n", encoding="utf-8")
    result = subprocess.run(
        ["jc-gha-audit", "scan", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "OK .github/workflows/ci.yml"
    assert result.stderr == ""


@pytest.mark.parametrize("directory_exists", [True, False])
def test_scan_without_workflows(tmp_path: Path, directory_exists: bool) -> None:
    if directory_exists:
        (tmp_path / ".github" / "workflows").mkdir(parents=True)
    result = subprocess.run(
        ["jc-gha-audit", "scan", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "No workflow files found."


def test_scan_invalid_repository(tmp_path: Path) -> None:
    result = subprocess.run(
        ["jc-gha-audit", "scan", str(tmp_path / "missing")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "Error discovering workflows:" in result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize(
    ("contents", "expected_code", "expected_ok", "expected_errors"),
    [
        (["on: push", "on: [push]"], 0, 2, 0),
        (["on: [", "on: push"], 1, 1, 1),
        (["on: [", "jobs: ["], 1, 0, 2),
    ],
)
def test_scan_multiple_workflows(
    tmp_path: Path,
    contents: list[str],
    expected_code: int,
    expected_ok: int,
    expected_errors: int,
) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    for index, content in enumerate(contents):
        (workflows / f"{index}.yml").write_text(content, encoding="utf-8")
    result = subprocess.run(
        ["jc-gha-audit", "scan", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == expected_code
    assert result.stdout.count("OK ") == expected_ok
    assert result.stderr.count("ERROR ") == expected_errors
    assert "Traceback" not in result.stderr
    for index, content in enumerate(contents):
        if content.endswith("["):
            assert f"{index}.yml" in result.stderr
            assert "expected" in result.stderr
        else:
            assert f".github/workflows/{index}.yml" in result.stdout


def test_findings_are_sorted_and_include_details(tmp_path: Path) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "z.yml").write_text("on: workflow_run\n", encoding="utf-8")
    (workflows / "a.yml").write_text(
        "on: [workflow_run, pull_request_target]\n"
        "permissions: write-all\n"
        "jobs:\n  build:\n    permissions:\n      contents: write\n",
        encoding="utf-8",
    )
    command = ["jc-gha-audit", "scan", str(tmp_path)]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    repeated = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 1
    assert result.stdout == repeated.stdout
    assert result.stderr == repeated.stderr == ""
    lines = [line for line in result.stdout.splitlines() if line.startswith("GHA")]
    assert [line.split()[0] for line in lines] == [
        "GHA001",
        "GHA002",
        "GHA003",
        "GHA004",
        "GHA002",
    ]
    assert all(".github/workflows/a.yml" in line for line in lines[:4])
    assert ".github/workflows/z.yml" in lines[4]
    assert "HIGH" in lines[2]
    assert all("MEDIUM" in lines[index] for index in (0, 1, 3, 4))
    assert result.stdout.count("Recommendation:") == 5


def test_findings_and_parse_errors_are_both_reported(tmp_path: Path) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "a.yml").write_text("on: [", encoding="utf-8")
    (workflows / "b.yml").write_text("on: pull_request_target", encoding="utf-8")
    result = subprocess.run(
        ["jc-gha-audit", "scan", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "ERROR" in result.stderr and "a.yml" in result.stderr
    assert "GHA001" in result.stdout and "b.yml" in result.stdout
    assert "Traceback" not in result.stderr


def test_pinning_findings_and_order_with_parse_error(tmp_path: Path) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "a.yml").write_text(
        "on: pull_request_target\n"
        "jobs:\n  build:\n    steps:\n"
        "      - uses: actions/checkout@v4\n"
        "      - uses: owner/action@main\n"
        "  reusable:\n    uses: owner/repo/.github/workflows/run.yml@main\n",
        encoding="utf-8",
    )
    (workflows / "b.yml").write_text("on: [", encoding="utf-8")
    command = ["jc-gha-audit", "scan", str(tmp_path)]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    repeated = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == repeated.returncode == 1
    assert result.stdout == repeated.stdout and result.stderr == repeated.stderr
    lines = [line for line in result.stdout.splitlines() if line.startswith("GHA")]
    assert [line.split()[0] for line in lines] == [
        "GHA001",
        "GHA005",
        "GHA005",
        "GHA006",
    ]
    assert "step 1" in lines[1] and "step 2" in lines[2]
    assert all("MEDIUM" in line and "a.yml" in line for line in lines)
    assert result.stdout.count("Recommendation:") == 4
    assert "ERROR" in result.stderr and "b.yml" in result.stderr


def test_pinned_and_local_references_are_clean(tmp_path: Path) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    sha = "abcdef0123" * 4
    (workflows / "ci.yml").write_text(
        "on: push\njobs:\n  build:\n    steps:\n"
        f"      - uses: actions/checkout@{sha}\n"
        "      - uses: ./local-action\n"
        f"  remote:\n    uses: owner/repo/.github/workflows/ci.yml@{sha}\n"
        "  local:\n    uses: ./.github/workflows/local.yml\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        ["jc-gha-audit", "scan", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "OK .github/workflows/ci.yml"
    assert result.stderr == ""


@pytest.mark.parametrize(
    ("disabled", "expected"),
    [
        ([], ["GHA001", "GHA002", "GHA003", "GHA004", "GHA005", "GHA006"]),
        (["GHA001"], ["GHA002", "GHA003", "GHA004", "GHA005", "GHA006"]),
        (["GHA002", "GHA003", "GHA005"], ["GHA001", "GHA004", "GHA006"]),
        (["GHA001", "GHA002", "GHA003", "GHA004", "GHA005", "GHA006"], []),
    ],
)
def test_scan_with_rule_configuration(
    tmp_path: Path, disabled: list[str], expected: list[str]
) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text(
        "on: [pull_request_target, workflow_run]\npermissions: write-all\n"
        "jobs:\n  build:\n    permissions: {contents: write}\n"
        "    steps:\n      - uses: actions/checkout@v4\n"
        "  reusable:\n    uses: owner/repo/.github/workflows/run.yml@main\n",
        encoding="utf-8",
    )
    config = tmp_path / "audit.yml"
    config.write_text(
        "disabled_rules: [" + ", ".join(disabled) + "]\n", encoding="utf-8"
    )
    result = subprocess.run(
        ["jc-gha-audit", "scan", str(tmp_path), "--config", str(config)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == bool(expected)
    assert [
        line.split()[0] for line in result.stdout.splitlines() if line.startswith("GHA")
    ] == expected
    assert result.stderr == ""


@pytest.mark.parametrize("content", ["disabled_rules: [GHA999]", "disabled_rules: ["])
def test_invalid_cli_configuration(tmp_path: Path, content: str) -> None:
    config = tmp_path / "audit.yml"
    config.write_text(content, encoding="utf-8")
    result = subprocess.run(
        ["jc-gha-audit", "scan", str(tmp_path), "--config", str(config)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "Error loading configuration:" in result.stderr
    assert "Traceback" not in result.stderr


def test_missing_cli_configuration_and_scan_help(tmp_path: Path) -> None:
    result = subprocess.run(
        ["jc-gha-audit", "scan", str(tmp_path), "--config", str(tmp_path / "missing")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1 and "unable to read" in result.stderr
    assert "Traceback" not in result.stderr
    help_result = subprocess.run(
        ["jc-gha-audit", "scan", "--help"], capture_output=True, text=True, check=False
    )
    assert help_result.returncode == 0 and "--config" in help_result.stdout


def test_disabled_rule_functions_are_not_called(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from jc_github_action_security_auditor import cli

    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text("on: push\n", encoding="utf-8")
    config = tmp_path / "audit.yml"
    config.write_text(
        "disabled_rules: [GHA001, GHA002, GHA003, GHA004, GHA005, GHA006]\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv", ["jc-gha-audit", "scan", str(tmp_path), "--config", str(config)]
    )
    with (
        patch.object(
            cli, "detect_privileged_triggers", side_effect=AssertionError("called")
        ),
        patch.object(
            cli, "detect_token_permissions", side_effect=AssertionError("called")
        ),
        patch.object(
            cli, "detect_unpinned_actions", side_effect=AssertionError("called")
        ),
        patch.object(
            cli,
            "detect_unpinned_reusable_workflows",
            side_effect=AssertionError("called"),
        ),
    ):
        assert cli.main() == 0


@pytest.mark.parametrize("report_format", ["json", "markdown"])
def test_structured_reports_with_errors_and_config(
    tmp_path: Path, report_format: str
) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "a.yml").write_text(
        "on: [pull_request_target, workflow_run]\npermissions: write-all\n",
        encoding="utf-8",
    )
    (workflows / "b.yml").write_text("on: [", encoding="utf-8")
    config = tmp_path / "config.yml"
    config.write_text("disabled_rules: [GHA002]\n", encoding="utf-8")
    command = [
        "jc-gha-audit",
        "scan",
        str(tmp_path),
        "--format",
        report_format,
        "--config",
        str(config),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    repeated = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 1 and result.stderr == ""
    assert result.stdout == repeated.stdout and result.stderr == repeated.stderr
    if report_format == "json":
        data = json.loads(result.stdout)
        assert data["summary"] == {"workflows_analyzed": 1, "findings": 2, "errors": 1}
        assert [finding["rule_id"] for finding in data["findings"]] == [
            "GHA001",
            "GHA003",
        ]
        assert data["findings"][0]["file_path"] == ".github/workflows/a.yml"
        assert data["errors"][0]["file_path"] == ".github/workflows/b.yml"
    else:
        assert "Workflows analyzed: 1" in result.stdout
        assert "Findings: 2" in result.stdout and "Errors: 1" in result.stdout
        assert result.stdout.index("GHA001") < result.stdout.index("GHA003")
        assert "GHA002" not in result.stdout and "## Workflow errors" in result.stdout


@pytest.mark.parametrize("report_format", ["json", "markdown"])
@pytest.mark.parametrize("has_workflow", [True, False])
def test_structured_empty_or_clean_scan(
    tmp_path: Path, report_format: str, has_workflow: bool
) -> None:
    if has_workflow:
        workflows = tmp_path / ".github" / "workflows"
        workflows.mkdir(parents=True)
        (workflows / "ci.yml").write_text("on: push\n", encoding="utf-8")
    result = subprocess.run(
        ["jc-gha-audit", "scan", str(tmp_path), "--format", report_format],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0 and result.stderr == ""
    if report_format == "json":
        data = json.loads(result.stdout)
        assert data["summary"] == {
            "workflows_analyzed": int(has_workflow),
            "findings": 0,
            "errors": 0,
        }
        assert data["findings"] == data["errors"] == []
    else:
        assert f"Workflows analyzed: {int(has_workflow)}" in result.stdout
        assert (
            "No findings." in result.stdout and "No workflow errors." in result.stdout
        )


def test_invalid_format_and_structured_operational_error(tmp_path: Path) -> None:
    invalid = subprocess.run(
        ["jc-gha-audit", "scan", str(tmp_path), "--format", "xml"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert invalid.returncode != 0 and "invalid choice" in invalid.stderr
    error = subprocess.run(
        [
            "jc-gha-audit",
            "scan",
            str(tmp_path),
            "--format",
            "json",
            "--config",
            str(tmp_path / "missing"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert error.returncode == 1 and error.stdout == ""
    assert "Error loading configuration" in error.stderr
    help_result = subprocess.run(
        ["jc-gha-audit", "scan", "--help"], capture_output=True, text=True, check=False
    )
    assert "--format" in help_result.stdout
