"""Tests for safe workflow YAML parsing."""

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from jc_github_action_security_auditor.parser import (
    MAX_WORKFLOW_SIZE_BYTES,
    WorkflowParseError,
    parse_workflow,
)


@pytest.mark.parametrize("extension", ["yml", "yaml"])
@pytest.mark.parametrize("trigger", ["push", "[push, pull_request]", "{push: {}}"])
def test_valid_workflows(tmp_path: Path, extension: str, trigger: str) -> None:
    path = tmp_path / f"ci.{extension}"
    path.write_text(
        f"on: {trigger}\nenabled: true\ndisabled: false\n", encoding="utf-8"
    )
    result = parse_workflow(path)
    assert "on" in result
    assert result["on"] == yaml.safe_load(trigger)
    assert result["enabled"] is True
    assert result["disabled"] is False


def test_boolean_resolver_is_local(tmp_path: Path) -> None:
    path = tmp_path / "ci.yml"
    path.write_text("on: off\nyes: no\n", encoding="utf-8")
    assert parse_workflow(path) == {"on": "off", "yes": "no"}
    assert yaml.safe_load("on: off") == {True: False}


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("key: [", "expected"),
        ("", "mapping"),
        ("- one\n- two", "mapping"),
        ("on: push\non: pull_request", "Duplicate mapping key"),
        ("jobs:\n  build: {}\n  build: {}", "Duplicate mapping key"),
        ("job: {<<: {x: 1}}", "merge keys"),
        ("a: &a [*a]", "aliases"),
        ("a: !!python/object/apply:os.system ['echo unsafe']", "constructor"),
        ("1: value", "Mapping keys must be strings"),
    ],
)
def test_invalid_yaml(tmp_path: Path, content: str, message: str) -> None:
    path = tmp_path / "ci.yml"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(WorkflowParseError, match=message) as exc:
        parse_workflow(path)
    assert str(path) in str(exc.value)


def test_duplicate_error_has_location(tmp_path: Path) -> None:
    path = tmp_path / "ci.yml"
    path.write_text("a: 1\na: 2\n", encoding="utf-8")
    with pytest.raises(WorkflowParseError, match=r":2:1: Duplicate"):
        parse_workflow(path)


def test_missing_and_unreadable_files(tmp_path: Path) -> None:
    path = tmp_path / "missing.yml"
    with pytest.raises(WorkflowParseError, match="unable to read"):
        parse_workflow(path)
    with (
        patch.object(
            Path, "open", side_effect=PermissionError(13, "Permission denied")
        ),
        pytest.raises(WorkflowParseError, match="Permission denied"),
    ):
        parse_workflow(path)


def test_invalid_encoding(tmp_path: Path) -> None:
    path = tmp_path / "ci.yml"
    path.write_bytes(b"\xff")
    with pytest.raises(WorkflowParseError, match="UTF-8"):
        parse_workflow(path)


def test_size_limit(tmp_path: Path) -> None:
    path = tmp_path / "ci.yml"
    path.write_bytes(b"a" * (MAX_WORKFLOW_SIZE_BYTES + 1))
    with pytest.raises(WorkflowParseError, match="size limit"):
        parse_workflow(path)


def test_expression_is_text(tmp_path: Path) -> None:
    path = tmp_path / "ci.yml"
    path.write_text("value: ${{ github.event.issue.title }}\n", encoding="utf-8")
    assert parse_workflow(path)["value"] == "${{ github.event.issue.title }}"


def test_excessive_nesting_is_controlled(tmp_path: Path) -> None:
    path = tmp_path / "ci.yml"
    path.write_text("a: " + "[" * 2000 + "]" * 2000, encoding="utf-8")
    with pytest.raises(WorkflowParseError, match="parser limits"):
        parse_workflow(path)
