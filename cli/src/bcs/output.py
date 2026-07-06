"""Result output helpers shared by every command.

Implements the ``CLI-005`` / ``CLI-012`` rules from ``docs/CLI.md``: a
command's *result* always goes to stdout, exactly once, in the format
``--output`` requests; every JSON payload carries a schema version so
scripts can detect a breaking change in the output shape independently
of the ClassroomConfig format (see
``docs/CLI.md#extensibility--versioning``).

Two ways a result carries its schema version, for two different kinds
of payload:

- :func:`print_structured_result` - for ad hoc command payloads
  (``doctor``, ``version``) that have no schema identity of their own;
  ``CLI_SCHEMA_VERSION`` (the CLI's own output-shape version) is added.
- :func:`print_model_result` - for a payload that is *already* a
  self-describing Pydantic model with its own ``schema_version`` field
  (e.g. ``HostInventory``, ``bcs-inventory/v1alpha1``) - printed as-is,
  never re-wrapped in ``CLI_SCHEMA_VERSION``, since a consumer reading
  that JSON (Boot Manager, Builder, Deploy, or a future REST API) cares
  about the data's own schema version, not the CLI's.
"""

from __future__ import annotations

import json
from enum import StrEnum
from typing import Any

import yaml
from pydantic import BaseModel
from rich.console import Console

#: Mirrors the ``apiVersion`` pattern used by ClassroomConfig
#: (see ADR-0005); bump this whenever a JSON output field is
#: removed/renamed (a MAJOR change, per CLI-011).
CLI_SCHEMA_VERSION = "bcs-cli/v1alpha1"


class OutputFormat(StrEnum):
    """Values accepted by ``--output``/``-o``."""

    TEXT = "text"
    JSON = "json"
    YAML = "yaml"


def with_schema_version(payload: dict[str, Any]) -> dict[str, Any]:
    """Return ``payload`` with ``schemaVersion`` set, per ``CLI-012``."""
    return {"schemaVersion": CLI_SCHEMA_VERSION, **payload}


def _print_json_or_yaml(
    console: Console, output_format: OutputFormat, data: dict[str, Any]
) -> None:
    if output_format is OutputFormat.JSON:
        console.print(json.dumps(data, indent=2, sort_keys=False))
    elif output_format is OutputFormat.YAML:
        console.print(yaml.safe_dump(data, sort_keys=False).rstrip())
    else:  # pragma: no cover - defensive; callers must not reach this
        msg = "structured output does not support OutputFormat.TEXT"
        raise ValueError(msg)


def print_structured_result(
    console: Console,
    output_format: OutputFormat,
    payload: dict[str, Any],
) -> None:
    """Print an ad hoc command payload, tagged with ``CLI_SCHEMA_VERSION``.

    Never used for ``OutputFormat.TEXT`` - text rendering is
    command-specific (Rich tables/panels) and handled by the caller.
    """
    _print_json_or_yaml(console, output_format, with_schema_version(payload))


def print_model_result(console: Console, output_format: OutputFormat, model: BaseModel) -> None:
    """Print a self-describing Pydantic model exactly as it serializes.

    Unlike :func:`print_structured_result`, this does *not* add
    ``CLI_SCHEMA_VERSION`` - ``model`` is expected to already carry its
    own schema version field (by convention). Never used for
    ``OutputFormat.TEXT``.
    """
    _print_json_or_yaml(console, output_format, model.model_dump(mode="json", by_alias=True))


__all__ = [
    "CLI_SCHEMA_VERSION",
    "OutputFormat",
    "print_model_result",
    "print_structured_result",
    "with_schema_version",
]
