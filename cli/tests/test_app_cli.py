from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from bcs.app import app
from bcs.commands import doctor as doctor_module
from bcs.exit_codes import ExitCode

runner = CliRunner()


def test_help_exits_zero_and_lists_all_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for name in (
        "doctor",
        "inventory",
        "validate",
        "version",
        "build",
        "install",
        "deploy",
        "backup",
        "restore",
        "update",
        "config",
    ):
        assert name in result.output


def test_inventory_command_runs_end_to_end() -> None:
    # --output is a global option; CliRunner invokes the Click command
    # directly, bypassing __main__.main()'s normalize_argv preprocessing,
    # so (unlike a real `bcs inventory --output json` invocation) it must
    # be given before the subcommand here - see test_argv_normalize.py.
    result = runner.invoke(app, ["--output", "json", "inventory"])
    assert result.exit_code == 0
    assert '"schemaVersion": "bcs-inventory/v1alpha1"' in result.output


def test_bare_invocation_shows_help_and_exits_zero() -> None:
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "Usage" in result.output


def test_version_command_text() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "bcs" in result.output


def test_root_version_flag_is_eager_and_terse() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.output.startswith("bcs ")


def test_unknown_command_exits_with_plugin_error_code() -> None:
    result = runner.invoke(app, ["definitely-not-a-command"])
    assert result.exit_code == int(ExitCode.PLUGIN_ERROR)


def test_unknown_command_with_close_match_suggests_it() -> None:
    result = runner.invoke(app, ["doctro"])
    assert result.exit_code == int(ExitCode.PLUGIN_ERROR)
    assert "doctor" in result.output


def test_validate_command_against_real_example(real_example_config_path: Path) -> None:
    result = runner.invoke(app, ["validate", str(real_example_config_path)])
    assert result.exit_code == 0


def test_validate_missing_file_is_usage_error() -> None:
    result = runner.invoke(app, ["validate", "no/such/file.yaml"])
    assert result.exit_code != 0


@pytest.mark.parametrize(
    "stub_name",
    ["build", "install", "deploy", "backup", "restore", "update", "config"],
)
def test_stub_commands_raise_with_general_error_exit_code(stub_name: str) -> None:
    """``CliRunner`` invokes the Click command directly, bypassing
    ``bcs.__main__.main``'s try/except - so it sees the raised
    exception, not the printed message. Message-content assertions for
    this path live in ``test_end_to_end.py``, which goes through the
    real entry point; this only pins down the exit code.
    """
    result = runner.invoke(app, [stub_name])
    assert result.exit_code == int(ExitCode.GENERAL_ERROR)
    assert isinstance(result.exception, Exception)
    assert "not implemented" in str(result.exception)


def test_doctor_command_runs_end_to_end(monkeypatch: pytest.MonkeyPatch) -> None:
    def _ok(_runtime: object) -> doctor_module.CheckResult:
        return doctor_module.CheckResult("fake", "ok", "fine")

    for name in doctor_module._ALL_CHECKS:
        monkeypatch.setitem(doctor_module._ALL_CHECKS, name, _ok)

    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0


def test_global_option_after_subcommand_via_normalize_argv() -> None:
    """app() itself does not reorder argv (that's __main__.main()'s job),
    so this exercises the reordering explicitly end to end.
    """
    from bcs.argv_normalize import normalize_argv

    result = runner.invoke(app, normalize_argv(["version", "--output", "json"]))
    assert result.exit_code == 0
    assert '"schemaVersion"' in result.output
