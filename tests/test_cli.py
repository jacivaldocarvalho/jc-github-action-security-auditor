"""Tests for the public command-line interface."""

import subprocess
from pathlib import Path

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
