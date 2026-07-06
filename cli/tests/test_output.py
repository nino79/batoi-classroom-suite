from __future__ import annotations

import json

from pydantic import BaseModel
from rich.console import Console

from bcs.output import (
    CLI_SCHEMA_VERSION,
    OutputFormat,
    print_model_result,
    print_structured_result,
    with_schema_version,
)


class _SelfDescribingModel(BaseModel):
    schema_version: str = "example/v1"
    value: int


def test_with_schema_version_prefixes_payload() -> None:
    result = with_schema_version({"a": 1})
    assert result == {"schemaVersion": CLI_SCHEMA_VERSION, "a": 1}


def test_print_structured_result_json(capsys_console: Console) -> None:
    print_structured_result(capsys_console, OutputFormat.JSON, {"valid": True})
    output = capsys_console.file.getvalue()  # type: ignore[attr-defined]
    payload = json.loads(output)
    assert payload["schemaVersion"] == CLI_SCHEMA_VERSION
    assert payload["valid"] is True


def test_print_structured_result_yaml(capsys_console: Console) -> None:
    print_structured_result(capsys_console, OutputFormat.YAML, {"valid": True})
    output = capsys_console.file.getvalue()  # type: ignore[attr-defined]
    assert "schemaVersion: " in output
    assert "valid: true" in output


def test_print_model_result_preserves_the_models_own_schema_version(
    capsys_console: Console,
) -> None:
    model = _SelfDescribingModel(value=42)
    print_model_result(capsys_console, OutputFormat.JSON, model)
    payload = json.loads(capsys_console.file.getvalue())  # type: ignore[attr-defined]
    assert payload == {"schema_version": "example/v1", "value": 42}
    assert payload["schema_version"] != CLI_SCHEMA_VERSION


def test_print_model_result_yaml(capsys_console: Console) -> None:
    model = _SelfDescribingModel(value=7)
    print_model_result(capsys_console, OutputFormat.YAML, model)
    output = capsys_console.file.getvalue()  # type: ignore[attr-defined]
    assert "schema_version: example/v1" in output
    assert "value: 7" in output
