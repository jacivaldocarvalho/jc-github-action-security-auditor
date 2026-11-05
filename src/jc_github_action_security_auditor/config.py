"""Immutable configuration for security rule selection."""

from dataclasses import dataclass
from pathlib import Path

import yaml

from jc_github_action_security_auditor.parser import (
    MAX_WORKFLOW_SIZE_BYTES,
    _WorkflowLoader,
)

SUPPORTED_RULES = frozenset(f"GHA{number:03d}" for number in range(1, 7))


@dataclass(frozen=True)
class RuleConfig:
    """Specify which supported security rules are enabled."""

    enabled_rules: frozenset[str] = SUPPORTED_RULES

    def __post_init__(self) -> None:
        enabled = frozenset(self.enabled_rules)
        unknown = enabled - SUPPORTED_RULES
        if unknown:
            raise ValueError(f"Unknown rule IDs: {', '.join(sorted(unknown))}")
        object.__setattr__(self, "enabled_rules", enabled)

    def is_enabled(self, rule_id: str) -> bool:
        """Return whether a supported rule is enabled."""
        if rule_id not in SUPPORTED_RULES:
            raise ValueError(f"Unknown rule ID: {rule_id}")
        return rule_id in self.enabled_rules

    def disable(self, *rule_ids: str) -> "RuleConfig":
        """Return a new configuration with the specified rules disabled."""
        unknown = set(rule_ids) - SUPPORTED_RULES
        if unknown:
            raise ValueError(f"Unknown rule IDs: {', '.join(sorted(unknown))}")
        return RuleConfig(self.enabled_rules.difference(rule_ids))


class ConfigError(ValueError):
    """A configuration file could not be safely loaded or validated."""


class _ConfigLoader(_WorkflowLoader):
    """Reject explicit tags in addition to the workflow loader's restrictions."""

    def compose_node(self, parent: object, index: object) -> yaml.Node:
        event = self.peek_event()
        if getattr(event, "tag", None) is not None:
            raise yaml.composer.ComposerError(
                None, None, "Explicit YAML tags are not supported", event.start_mark
            )
        return super().compose_node(parent, index)


def load_config(path: Path) -> RuleConfig:
    """Load and validate a local YAML rule configuration."""
    path = Path(path)
    try:
        with path.open("rb") as stream:
            contents = stream.read(MAX_WORKFLOW_SIZE_BYTES + 1)
    except OSError as error:
        raise ConfigError(
            f"{path}: unable to read configuration: {error.strerror}"
        ) from error
    if len(contents) > MAX_WORKFLOW_SIZE_BYTES:
        raise ConfigError(f"{path}: configuration exceeds the 1 MiB size limit")
    try:
        text = contents.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ConfigError(f"{path}: configuration is not valid UTF-8") from error
    try:
        loader = _ConfigLoader(text)
        try:
            node = loader.get_single_node()
            document = {} if node is None else loader.construct_document(node)
        finally:
            loader.dispose()
    except yaml.YAMLError as error:
        mark = getattr(error, "problem_mark", None)
        location = f":{mark.line + 1}:{mark.column + 1}" if mark else ""
        problem = getattr(error, "problem", None) or "Invalid YAML"
        raise ConfigError(f"{path}{location}: {problem}") from error
    except (RecursionError, ValueError, OverflowError) as error:
        raise ConfigError(
            f"{path}: YAML exceeds parser limits or is invalid"
        ) from error
    if not isinstance(document, dict):
        raise ConfigError(f"{path}: configuration must be a mapping")
    unknown = document.keys() - {"disabled_rules"}
    if unknown:
        raise ConfigError(
            f"{path}: unknown configuration keys: {', '.join(sorted(unknown))}"
        )
    disabled = document.get("disabled_rules", [])
    if not isinstance(disabled, list) or not all(
        isinstance(rule, str) for rule in disabled
    ):
        raise ConfigError(f"{path}: disabled_rules must be a list of rule ID strings")
    if len(disabled) != len(set(disabled)):
        raise ConfigError(f"{path}: disabled_rules must not contain duplicates")
    try:
        return RuleConfig().disable(*disabled)
    except ValueError as error:
        raise ConfigError(f"{path}: {error}") from error
