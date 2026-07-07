"""The run's dependency-injection container.

``bcs.app``'s root Typer callback builds exactly one
:class:`RuntimeContext` per invocation and stores it on ``ctx.obj``.
Every command function receives it as a constructor argument rather
than reaching for globals, ``os.environ``, or `sys.argv` itself - the
context is the single seam through which every collaborator (console,
logger, config loader, preferences, the Platform Layer's
``CommandRunner``) is injected, so commands stay unit testable without
patching module state.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rich.console import Console

from bcs.config.loader import ConfigLoader
from bcs.config.preferences import CliPreferences
from bcs.inventory.discovery.orchestrator import HostDiscoveryOrchestrator
from bcs.logging_setup import LogFormat, LogLevel
from bcs.output import OutputFormat
from bcs.platform.execution import CommandRunner


@dataclass(frozen=True)
class RuntimeContext:
    """Everything a command needs, resolved once at startup.

    ``command_runner`` is the single Platform Layer seam every future
    service must obtain its :class:`~bcs.platform.execution.CommandRunner`
    through - see ``docs/PLATFORM_LAYER.md#dependency-injection``. It is
    built once, in ``bcs.app``'s root callback, and reused for the
    lifetime of the invocation, exactly like every other collaborator
    on this dataclass; there is no module-level singleton or service
    locator anywhere in the Platform Layer.

    ``host_discovery_orchestrator`` receives the same treatment - see
    ``docs/HOST_DISCOVERY_ORCHESTRATOR.md#lifecycle---implemented``. It is built once,
    in ``bcs.app``'s root callback, from a
    :class:`~bcs.inventory.discovery.models.HostDiscoveryAdapters` bundle
    whose tool-based slots are bound to the very same ``command_runner``
    above - never a second, independently constructed one.
    """

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
    command_runner: CommandRunner
    host_discovery_orchestrator: HostDiscoveryOrchestrator


__all__ = ["RuntimeContext"]
