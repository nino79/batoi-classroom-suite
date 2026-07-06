from __future__ import annotations

from pathlib import Path

from bcs.config.preferences import CliPreferences, load_preferences, preferences_path


def test_preferences_path_uses_xdg_config_home() -> None:
    path = preferences_path(env={"XDG_CONFIG_HOME": "/custom/config"})
    assert path == Path("/custom/config/bcs/cli.yaml")


def test_preferences_path_falls_back_to_home_dot_config() -> None:
    path = preferences_path(env={})
    assert path.parts[-3:] == (".config", "bcs", "cli.yaml")


def test_load_preferences_returns_defaults_when_absent(tmp_path: Path) -> None:
    prefs = load_preferences(tmp_path / "nonexistent.yaml")
    assert prefs == CliPreferences()
    assert prefs.color == "auto"
    assert prefs.no_input is False
    assert prefs.default_config is None


def test_load_preferences_reads_yaml(tmp_path: Path) -> None:
    path = tmp_path / "cli.yaml"
    path.write_text(
        "color: always\noutput: json\nlogLevel: debug\nnoInput: true\n",
        encoding="utf-8",
    )
    prefs = load_preferences(path)
    assert prefs.color == "always"
    assert prefs.output == "json"
    assert prefs.log_level == "debug"
    assert prefs.no_input is True


def test_load_preferences_ignores_unknown_fields(tmp_path: Path) -> None:
    path = tmp_path / "cli.yaml"
    path.write_text("color: always\nsomethingBcsDoesNotKnowAbout: true\n", encoding="utf-8")
    prefs = load_preferences(path)
    assert prefs.color == "always"


def test_load_preferences_handles_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "cli.yaml"
    path.write_text("", encoding="utf-8")
    prefs = load_preferences(path)
    assert prefs == CliPreferences()
