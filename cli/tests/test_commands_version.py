from __future__ import annotations

import json
from pathlib import Path

from bcs.commands.version import run_version
from bcs.output import OutputFormat


def test_version_always_returns_zero_with_no_config(make_runtime_context) -> None:
    runtime = make_runtime_context(output=OutputFormat.JSON)
    code = run_version(runtime)
    assert code == 0
    payload = json.loads(runtime.console.file.getvalue())
    assert payload["loadedConfig"] is None
    assert payload["supportedConfigApiVersions"] == ["bcs/v1alpha1"]
    assert payload["schemaVersion"] == "bcs-cli/v1alpha1"


def test_version_reports_compatible_config(make_runtime_context, valid_config_path: Path) -> None:
    runtime = make_runtime_context(config_path=valid_config_path, output=OutputFormat.JSON)
    run_version(runtime)
    payload = json.loads(runtime.console.file.getvalue())
    assert payload["loadedConfig"]["compatible"] is True
    assert payload["loadedConfig"]["apiVersion"] == "bcs/v1alpha1"


def test_version_reports_incompatible_config_without_erroring(
    make_runtime_context, tmp_path: Path
) -> None:
    bad = tmp_path / "bcs.yaml"
    bad.write_text("apiVersion: bcs/v1alpha1\nkind: [unterminated", encoding="utf-8")
    runtime = make_runtime_context(config_path=bad, output=OutputFormat.JSON)
    code = run_version(runtime)
    assert code == 0
    payload = json.loads(runtime.console.file.getvalue())
    assert payload["loadedConfig"]["compatible"] is False


def test_version_text_output_does_not_crash(make_runtime_context) -> None:
    runtime = make_runtime_context(output=OutputFormat.TEXT)
    code = run_version(runtime)
    assert code == 0
    assert "bcs" in runtime.console.file.getvalue()
