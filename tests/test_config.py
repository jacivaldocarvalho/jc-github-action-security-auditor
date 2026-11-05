"""Tests for immutable rule configuration."""

from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

import pytest

from jc_github_action_security_auditor.config import (
    SUPPORTED_RULES,
    ConfigError,
    RuleConfig,
    load_config,
)
from jc_github_action_security_auditor.parser import MAX_WORKFLOW_SIZE_BYTES


def test_all_rules_enabled_by_default() -> None:
    config = RuleConfig()
    assert config.enabled_rules == {f"GHA{number:03d}" for number in range(1, 7)}
    assert all(config.is_enabled(rule_id) for rule_id in SUPPORTED_RULES)


def test_disable_rules_without_changing_original() -> None:
    original = RuleConfig()
    config = original.disable("GHA001", "GHA003")
    assert not config.is_enabled("GHA001")
    assert not config.is_enabled("GHA003")
    assert config.is_enabled("GHA002")
    assert original.is_enabled("GHA001")
    assert not original.disable("GHA002").is_enabled("GHA002")


def test_unknown_rules_are_rejected() -> None:
    with pytest.raises(ValueError, match="GHA999"):
        RuleConfig(frozenset({"GHA999"}))
    with pytest.raises(ValueError, match="GHA999"):
        RuleConfig().disable("GHA999")
    with pytest.raises(ValueError, match="GHA999"):
        RuleConfig().is_enabled("GHA999")


def test_configuration_is_immutable_and_copies_input() -> None:
    source = {"GHA001"}
    config = RuleConfig(source)
    source.add("GHA002")
    assert config.enabled_rules == frozenset({"GHA001"})
    with pytest.raises(FrozenInstanceError):
        config.enabled_rules = frozenset()
    with pytest.raises(AttributeError):
        config.enabled_rules.add("GHA002")


def test_instances_are_independent() -> None:
    first = RuleConfig().disable("GHA001")
    second = RuleConfig().disable("GHA002")
    assert first.is_enabled("GHA002")
    assert second.is_enabled("GHA001")
    assert not first.is_enabled("GHA001")
    assert not second.is_enabled("GHA002")


def test_load_disabled_rules(tmp_path: Path) -> None:
    path = tmp_path / "config.yml"
    path.write_text("disabled_rules:\n  - GHA001\n  - GHA005\n", encoding="utf-8")
    config = load_config(path)
    assert not config.is_enabled("GHA001")
    assert not config.is_enabled("GHA005")
    assert config.is_enabled("GHA006")


@pytest.mark.parametrize("content", ["", "# comment\n", "{}", "disabled_rules: []"])
def test_load_empty_config(tmp_path: Path, content: str) -> None:
    path = tmp_path / "config.yml"
    path.write_text(content, encoding="utf-8")
    assert load_config(path) == RuleConfig()


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("other: []", "unknown configuration keys"),
        ("disabled_rules: [GHA999]", "GHA999"),
        ("disabled_rules: [GHA001, GHA001]", "duplicates"),
        ("disabled_rules: GHA001", "must be a list"),
        ("disabled_rules: [1]", "must be a list"),
        ("disabled_rules: null", "must be a list"),
        ("[]", "must be a mapping"),
        ("null", "must be a mapping"),
        ("disabled_rules: [", "expected"),
        ("disabled_rules: []\ndisabled_rules: []", "Duplicate mapping key"),
        ("disabled_rules: &x []\nother: *x", "aliases"),
        ("disabled_rules: !!python/object/apply:os.system ['echo unsafe']", "tags"),
        ("<<: {disabled_rules: []}", "merge keys"),
    ],
)
def test_invalid_config(tmp_path: Path, content: str, message: str) -> None:
    path = tmp_path / "config.yml"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ConfigError, match=message) as error:
        load_config(path)
    assert str(path) in str(error.value)


def test_missing_and_unreadable_config(tmp_path: Path) -> None:
    path = tmp_path / "missing.yml"
    with pytest.raises(ConfigError, match="unable to read"):
        load_config(path)
    with (
        patch.object(
            Path, "open", side_effect=PermissionError(13, "Permission denied")
        ),
        pytest.raises(ConfigError, match="Permission denied"),
    ):
        load_config(path)


def test_oversized_and_invalid_utf8_config(tmp_path: Path) -> None:
    path = tmp_path / "config.yml"
    path.write_bytes(b"x" * (MAX_WORKFLOW_SIZE_BYTES + 1))
    with pytest.raises(ConfigError, match="size limit"):
        load_config(path)
    path.write_bytes(b"\xff")
    with pytest.raises(ConfigError, match="UTF-8"):
        load_config(path)
