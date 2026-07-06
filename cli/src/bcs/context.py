"""The run's dependency-injection container.

``bcs.app``'s root Typer callback builds exactly one
:class:`RuntimeContext` per invocation and stores it on ``ctx.obj``.
Every command function receives it as a constructor argument rather
than reaching for globals, ``os.environ``, or `sys.argv` itself - the
context is the single seam through which every collaborator (console,
logger, config loader, preferences) is injected, so commands stay unit
testable without patching module state.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rich.console import Console

from bcs.config.loader import ConfigLoader
from bcs.config.preferences import CliPreferences
from bcs.logging_setup import LogFormat, LogLevel
from bcs.output import OutputFormat


@dataclass(frozen=True)
class RuntimeContext:
    """Everything a command needs, resolved once at startup."""

    invocation_id: str
    console: Console
    err_console: Console
    output: OutputFormat
    log_level: LogLevel
    log_format: LogFormat
    log_file: Path | None
    no_input: bool
    yes: bool
    dry_run: bool
    timeout: str | None
    config_loader: ConfigLoader
    preferences: CliPreferences


__all__ = ["RuntimeContext"]
