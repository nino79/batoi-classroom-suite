from __future__ import annotations

import os
from pathlib import Path

import pytest

from bcs.plugins import find_plugin, run_plugin, suggest_command


def test_find_plugin_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", "")
    assert find_plugin("definitely-not-a-real-plugin-name") is None


def test_find_plugin_discovers_executable_on_path(
    fake_plugin: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PATH", str(fake_plugin) + os.pathsep + os.environ.get("PATH", ""))
    found = find_plugin("hello")
    assert found is not None
    assert Path(found).exists()


def test_run_plugin_forwards_exit_code(fake_plugin: Path) -> None:
    script = fake_plugin / "bcs-hello"
    if not script.exists():
        script = fake_plugin / "bcs-hello.cmd"
    code = run_plugin(str(script), [], env=dict(os.environ))
    assert code == 0


def test_suggest_command_finds_close_typo() -> None:
    assert suggest_command("doctro", ["doctor", "validate", "version"]) == "doctor"


def test_suggest_command_returns_none_for_unrelated_input() -> None:
    assert suggest_command("xyzzyplugh", ["doctor", "validate", "version"]) is None
