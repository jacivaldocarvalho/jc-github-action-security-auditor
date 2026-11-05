"""Safely parse untrusted workflow YAML without executing its contents."""

import re
from pathlib import Path
from typing import ClassVar

import yaml
from yaml.constructor import ConstructorError
from yaml.events import AliasEvent
from yaml.nodes import MappingNode

MAX_WORKFLOW_SIZE_BYTES = 1024 * 1024


class WorkflowParseError(Exception):
    """A workflow could not be safely read or parsed."""


class _WorkflowLoader(yaml.SafeLoader):
    """Safe loader with isolated boolean and mapping policies."""

    yaml_implicit_resolvers: ClassVar[dict] = {
        key: [
            (tag, regex) for tag, regex in resolvers if tag != "tag:yaml.org,2002:bool"
        ]
        for key, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
    }

    def compose_node(self, parent: object, index: object) -> yaml.Node:
        if self.check_event(AliasEvent):
            event = self.peek_event()
            raise yaml.composer.ComposerError(
                None, None, "YAML aliases are not supported", event.start_mark
            )
        return super().compose_node(parent, index)

    def construct_mapping(self, node: MappingNode, deep: bool = False) -> dict:
        mapping = {}
        for key_node, value_node in node.value:
            if key_node.tag == "tag:yaml.org,2002:merge":
                raise ConstructorError(
                    None, None, "YAML merge keys are not supported", key_node.start_mark
                )
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                raise ConstructorError(
                    None, None, "Mapping keys must be strings", key_node.start_mark
                )
            if key in mapping:
                raise ConstructorError(
                    None, None, "Duplicate mapping key", key_node.start_mark
                )
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


_WorkflowLoader.add_implicit_resolver(
    "tag:yaml.org,2002:bool",
    re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"),
    list("tTfF"),
)


def parse_workflow(path: Path) -> dict[str, object]:
    """Read and parse a workflow mapping, raising WorkflowParseError on failure."""
    path = Path(path)
    try:
        with path.open("rb") as stream:
            contents = stream.read(MAX_WORKFLOW_SIZE_BYTES + 1)
    except OSError as error:
        raise WorkflowParseError(
            f"{path}: unable to read workflow: {error.strerror}"
        ) from error
    if len(contents) > MAX_WORKFLOW_SIZE_BYTES:
        raise WorkflowParseError(f"{path}: workflow exceeds the 1 MiB size limit")
    try:
        text = contents.decode("utf-8")
    except UnicodeDecodeError as error:
        raise WorkflowParseError(f"{path}: workflow is not valid UTF-8") from error
    try:
        document = yaml.load(text, Loader=_WorkflowLoader)
    except yaml.YAMLError as error:
        mark = getattr(error, "problem_mark", None)
        location = f":{mark.line + 1}:{mark.column + 1}" if mark else ""
        problem = getattr(error, "problem", None) or "Invalid YAML"
        raise WorkflowParseError(f"{path}{location}: {problem}") from error
    except (RecursionError, ValueError, OverflowError) as error:
        raise WorkflowParseError(
            f"{path}: YAML exceeds parser limits or is invalid"
        ) from error
    if not isinstance(document, dict):
        raise WorkflowParseError(
            f"{path}: workflow must be a nonempty YAML document containing a mapping"
        )
    return document
