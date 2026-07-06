"""Dotted-path get/set and the ``--set``/``BCS_CFG_*`` override layers.

Implements the precedence in
``docs/CLI.md#value-overrides-within-a-resolved-classroomconfig``:
``--set`` > ``BCS_CFG_*`` env vars > file value > schema default (schema
defaults are simply whatever the Pydantic models declare, applied last
by virtue of being the fallback when no override touched a field).
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from typing import Any

from bcs.errors import UsageError

_ENV_PREFIX = "BCS_CFG_"


def _split_path(path: str) -> list[str]:
    if not path:
        msg = "empty configuration path"
        raise UsageError(msg)
    return path.split(".")


def get_by_path(document: Mapping[str, Any], path: str) -> Any:
    """Read a value at a dotted path (array indices as numeric segments)."""
    node: Any = document
    for segment in _split_path(path):
        if isinstance(node, Mapping):
            if segment not in node:
                msg = f"no such field: {path!r} (missing at {segment!r})"
                raise UsageError(msg)
            node = node[segment]
        elif isinstance(node, list):
            try:
                index = int(segment)
            except ValueError as exc:
                msg = f"expected a numeric index at {segment!r} in {path!r}"
                raise UsageError(msg) from exc
            try:
                node = node[index]
            except IndexError as exc:
                msg = f"index {index} out of range in {path!r}"
                raise UsageError(msg) from exc
        else:
            msg = f"cannot descend into scalar value at {segment!r} in {path!r}"
            raise UsageError(msg)
    return node


def set_by_path(document: MutableMapping[str, Any], path: str, value: Any) -> None:
    """Write ``value`` at a dotted path, creating intermediate dicts as needed."""
    segments = _split_path(path)
    node: MutableMapping[str, Any] = document
    for segment in segments[:-1]:
        nxt = node.get(segment)
        if nxt is None:
            nxt = {}
            node[segment] = nxt
        if not isinstance(nxt, MutableMapping):
            msg = f"cannot descend into non-mapping value at {segment!r} in {path!r}"
            raise UsageError(msg)
        node = nxt
    node[segments[-1]] = value


def _coerce_scalar(raw: str) -> Any:
    """Best-effort YAML-like scalar coercion for ``--set``/env string values."""
    lowered = raw.strip().lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "~", "none"}:
        return None
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    return raw


def parse_set_option(item: str) -> tuple[str, Any]:
    """Parse one ``--set path=value`` argument."""
    if "=" not in item:
        msg = f"--set expects path=value, got {item!r}"
        raise UsageError(msg)
    path, _, raw_value = item.partition("=")
    path = path.strip()
    if not path:
        msg = f"--set expects a non-empty path, got {item!r}"
        raise UsageError(msg)
    return path, _coerce_scalar(raw_value)


def apply_set_overrides(document: MutableMapping[str, Any], overrides: list[str]) -> None:
    """Apply ``--set`` overrides in the order given (highest precedence)."""
    for item in overrides:
        path, value = parse_set_option(item)
        set_by_path(document, path, value)


def _find_actual_key(node: Mapping[str, Any], upper_segment: str) -> str | None:
    """Case-insensitively find ``node``'s real (camelCase) key for a segment.

    Environment variables are uppercase by convention
    (``docs/CLI.md#value-overrides-within-a-resolved-classroomconfig``),
    which loses the original camelCase shape of a key like ``secureBoot``
    (both ``secureBoot`` and ``secureboot`` uppercase to the same
    ``SECUREBOOT``). We recover the real casing by matching against the
    document itself rather than guessing.
    """
    for key in node:
        if key.upper() == upper_segment:
            return key
    return None


def _env_key_to_path(env_key: str, document: Mapping[str, Any]) -> str:
    """Resolve an env var name to a dotted path, case-corrected against
    the current document structure wherever a matching key exists.

    Segments that can't be matched (the field doesn't exist yet, or a
    prior segment wasn't itself a mapping) fall back to a lowercase
    best guess; ``set_by_path`` will then create it verbatim, and
    Pydantic validation surfaces a clear "unexpected property" error
    downstream if that guess was wrong - overriding a nonexistent field
    is a configuration mistake worth surfacing, not silently ignoring.
    """
    segments = env_key[len(_ENV_PREFIX) :].split("_")
    resolved: list[str] = []
    node: Any = document
    for index, segment in enumerate(segments):
        if isinstance(node, Mapping):
            actual = _find_actual_key(node, segment) or segment.lower()
            resolved.append(actual)
            node = node.get(actual)
        else:
            resolved.extend(s.lower() for s in segments[index:])
            break
    return ".".join(resolved)


def apply_env_overrides(
    document: MutableMapping[str, Any],
    env: Mapping[str, str],
) -> None:
    """Apply ``BCS_CFG_*`` environment overrides, below ``--set`` in precedence."""
    for key, raw_value in env.items():
        if not key.startswith(_ENV_PREFIX):
            continue
        path = _env_key_to_path(key, document)
        set_by_path(document, path, _coerce_scalar(raw_value))


__all__ = [
    "apply_env_overrides",
    "apply_set_overrides",
    "get_by_path",
    "parse_set_option",
    "set_by_path",
]
