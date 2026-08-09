from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import TypeVar, cast

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode

from esim.errors import ConfigurationError

_YamlError = TypeVar("_YamlError", bound=Exception)


def decode_configuration(text: str, source: Path) -> object:
    try:
        _validate_canonical_hook_booleans(text, source)
        return cast(object, yaml.safe_load(text))
    except yaml.YAMLError as error:
        raise ConfigurationError(
            f"cannot load YAML configuration\n  source: {source}\n  reason: {error}"
        ) from error


def decode_mapping(
    text: str,
    label: str,
    error_type: type[_YamlError],
) -> dict[str, object]:
    try:
        loaded = cast(object, yaml.safe_load(text))
    except yaml.YAMLError as error:
        raise error_type(f"cannot parse {label}\n  reason: {error}") from error
    if not isinstance(loaded, dict):
        raise error_type(f"{label} must contain a YAML mapping")
    mapping = cast(dict[object, object], loaded)
    if any(not isinstance(key, str) for key in mapping):
        raise error_type(f"{label} contains a non-string key")
    return cast(dict[str, object], mapping)


def encode_mapping(mapping: Mapping[str, object]) -> str:
    return yaml.safe_dump(
        dict(mapping),
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    )


def _validate_canonical_hook_booleans(text: str, source: Path) -> None:
    loader = yaml.SafeLoader(text)
    root = loader.get_single_node()
    if root is None or not isinstance(root, MappingNode):
        return

    def child(mapping: Node, key: str) -> Node | None:
        if not isinstance(mapping, MappingNode):
            return None
        for key_node, value_node in mapping.value:
            if isinstance(key_node, ScalarNode) and key_node.value == key:
                return value_node
        return None

    def validate_hook(hook: Node | None, field: str) -> None:
        if hook is None:
            return
        value = child(hook, "continue_on_error")
        if value is None:
            return
        if (
            not isinstance(value, ScalarNode)
            or value.tag != "tag:yaml.org,2002:bool"
            or value.value not in {"true", "false"}
        ):
            raise ConfigurationError(
                "continue_on_error must use lowercase true or false\n"
                f"  source: {source}\n"
                f"  field: {field}.continue_on_error"
            )

    def validate_phase(phase: Node | None, field: str) -> None:
        hooks = child(phase, "hooks") if phase is not None else None
        validate_hook(
            child(hooks, "before") if hooks else None,
            f"{field}.hooks.before",
        )
        validate_hook(
            child(hooks, "after") if hooks else None,
            f"{field}.hooks.after",
        )

    validate_phase(child(root, "ff"), "ff")
    build = child(root, "build")
    validate_phase(build, "build")
    if build is not None:
        validate_phase(child(build, "analyze"), "build.analyze")
        validate_phase(child(build, "elaborate"), "build.elaborate")
    validate_phase(child(root, "run"), "run")


__all__ = ["decode_configuration", "decode_mapping", "encode_mapping"]
