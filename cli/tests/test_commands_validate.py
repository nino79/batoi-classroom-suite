from __future__ import annotations

import json
from pathlib import Path

import pytest

from bcs.commands.validate import run_validate
from bcs.errors import ConfigInvalidError
from bcs.output import OutputFormat


def test_valid_config_returns_zero(make_runtime_context, valid_config_path: Path) -> None:
    runtime = make_runtime_context(config_path=valid_config_path)
    assert run_validate(runtime, files=[valid_config_path]) == 0


def test_no_files_resolves_via_config_loader(make_runtime_context, valid_config_path: Path) -> None:
    runtime = make_runtime_context(config_path=valid_config_path)
    assert run_validate(runtime, files=None) == 0


def test_invalid_config_raises_config_invalid_error(
    make_runtime_context, tmp_path: Path, valid_config_data: dict
) -> None:
    import yaml

    data = dict(valid_config_data)
    data["spec"]["bootManager"]["menu"]["defaultEntry"] = "does-not-exist"
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")

    runtime = make_runtime_context(output=OutputFormat.JSON)
    with pytest.raises(ConfigInvalidError):
        run_validate(runtime, files=[path])


def test_multiple_files_all_validated(
    make_runtime_context, valid_config_path: Path, tmp_path: Path
) -> None:
    second = tmp_path / "second.yaml"
    second.write_text(valid_config_path.read_text(encoding="utf-8"), encoding="utf-8")
    runtime = make_runtime_context(output=OutputFormat.JSON)
    assert run_validate(runtime, files=[valid_config_path, second]) == 0
    payload = json.loads(runtime.console.file.getvalue())
    assert len(payload["results"]) == 2


def test_strict_escalates_warnings_to_failure(
    make_runtime_context, tmp_path: Path, valid_config_data: dict
) -> None:
    import yaml

    data = dict(valid_config_data)
    data["spec"]["network"] = {"addressing": {"mode": "static"}}
    path = tmp_path / "warn.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")

    runtime = make_runtime_context()
    assert run_validate(runtime, files=[path], strict=False) == 0
    with pytest.raises(ConfigInvalidError):
        run_validate(runtime, files=[path], strict=True)
