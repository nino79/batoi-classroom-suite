"""End-to-end tests through the real process entry point
(:func:`bcs.__main__.main`), not just the Click/Typer app object.

``typer.testing.CliRunner`` (used in ``test_app_cli.py``) invokes the
Click command directly and never exercises ``bcs.__main__``'s
try/except - the one place that turns a raised ``BcsError`` into a
printed message and the documented exit code. These tests patch
``sys.argv`` and call ``main()`` itself, using ``capsys`` to observe
exactly what a real invocation of the ``bcs`` executable would print.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import bcs.__main__ as main_module
from bcs.exit_codes import ExitCode


def _run(monkeypatch: pytest.MonkeyPatch, argv: list[str]) -> int:
    monkeypatch.setattr("sys.argv", ["bcs", *argv])
    with pytest.raises(SystemExit) as exc_info:
        main_module.main()
    return int(exc_info.value.code)


def test_stub_command_prints_message_and_exits_general_error(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    code = _run(monkeypatch, ["build"])
    assert code == int(ExitCode.GENERAL_ERROR)
    captured = capsys.readouterr()
    assert "bcs: error:" in captured.err
    assert "not implemented in this phase" in captured.err
    assert captured.out == ""


def test_validate_success_prints_to_stdout_only(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    real_example_config_path: Path,
) -> None:
    code = _run(monkeypatch, ["validate", str(real_example_config_path)])
    assert code == 0
    captured = capsys.readouterr()
    assert "valid" in captured.out


def test_validate_failure_prints_error_to_stderr(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("apiVersion: bcs/v1alpha1\nkind: [unterminated", encoding="utf-8")
    code = _run(monkeypatch, ["validate", str(bad)])
    assert code == int(ExitCode.CONFIG_INVALID)
    captured = capsys.readouterr()
    assert "bcs: error:" in captured.err


def test_version_end_to_end() -> None:
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "bcs", "version"],
        capture_output=True,
        text=True,
        check=False,
        cwd=Path(__file__).parents[1],
    )
    assert result.returncode == 0
    assert "bcs" in result.stdout
