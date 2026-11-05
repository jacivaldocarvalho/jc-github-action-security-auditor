"""Tests for local workflow discovery."""

from pathlib import Path
from unittest.mock import patch

import pytest

from jc_github_action_security_auditor.discovery import discover_workflows


def test_discovers_sorted_workflows_without_reading_contents(tmp_path: Path) -> None:
    directory = tmp_path / ".github" / "workflows"
    directory.mkdir(parents=True)
    first = directory / "a.yaml"
    second = directory / "z.yml"
    first.touch()
    second.touch()
    (directory / "ignored.txt").touch()
    (directory / "nested.yml").mkdir()
    (directory / "nested.yml" / "nested.yml").touch()
    (directory / "linked.yml").symlink_to(first)
    with patch.object(Path, "open", side_effect=AssertionError("Contents were read")):
        assert discover_workflows(tmp_path) == [first, second]


def test_missing_workflows_directory(tmp_path: Path) -> None:
    assert discover_workflows(tmp_path) == []


def test_empty_workflows_directory(tmp_path: Path) -> None:
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    assert discover_workflows(tmp_path) == []


def test_missing_repository(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        discover_workflows(tmp_path / "missing")


def test_repository_is_file(tmp_path: Path) -> None:
    path = tmp_path / "file"
    path.touch()
    with pytest.raises(NotADirectoryError):
        discover_workflows(path)


@pytest.mark.parametrize("linked_component", [".github", "workflows"])
def test_linked_workflow_directories_are_rejected(
    tmp_path: Path, linked_component: str
) -> None:
    target = tmp_path / "target"
    target.mkdir()
    if linked_component == ".github":
        link = tmp_path / ".github"
    else:
        (tmp_path / ".github").mkdir()
        link = tmp_path / ".github" / "workflows"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match="symbolic link"):
        discover_workflows(tmp_path)


def test_inaccessible_directory_is_not_treated_as_empty(tmp_path: Path) -> None:
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    with (
        patch.object(Path, "iterdir", side_effect=PermissionError("Access denied")),
        pytest.raises(PermissionError),
    ):
        discover_workflows(tmp_path)
