"""The CLI preferences file, per ``docs/CLI.md#cli-preferences-file``.

Deliberately separate from :class:`~bcs.config.models.ClassroomConfig`:
this file holds personal workstation ergonomics (color, default output
format, a convenience default config path), never the platform
configuration itself - see the doc for the ``~/.gitconfig`` analogy.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field


class CliPreferences(BaseModel):
    """Optional personal defaults, all overridable by flags/env vars."""

    model_config = ConfigDict(extra="ignore")

    color: str = "auto"
    output: str = "text"
    log_level: str | None = Field(alias="logLevel", default=None)
    no_input: bool = Field(alias="noInput", default=False)
    default_config: Path | None = Field(alias="defaultConfig", default=None)


def preferences_path(*, env: dict[str, str] | None = None) -> Path:
    """Return ``$XDG_CONFIG_HOME/bcs/cli.yaml``, falling back to ``~/.config``."""
    environ = env if env is not None else dict(os.environ)
    xdg_config_home = environ.get("XDG_CONFIG_HOME")
    base = Path(xdg_config_home) if xdg_config_home else Path.home() / ".config"
    return base / "bcs" / "cli.yaml"


def load_preferences(path: Path | None = None) -> CliPreferences:
    """Load the CLI preferences file, or built-in defaults if absent/empty."""
    target = path if path is not None else preferences_path()
    if not target.is_file():
        return CliPreferences()

    data = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        return CliPreferences()
    return CliPreferences.model_validate(data)


__all__ = ["CliPreferences", "load_preferences", "preferences_path"]
