"""Root Typer app: global options, plugin dispatch, command registration.

This module is the composition root. It is the only place that reads
``sys.argv``/``os.environ`` and constructs collaborators (the
:class:`~bcs.config.loader.ConfigLoader`, Rich consoles, the logger);
everything downstream receives them already built via
:class:`~bcs.context.RuntimeContext` (``ctx.obj``) - see
``docs/CLI.md`` for the design this implements end to end.
"""

from __future__ import annotations

import contextlib
import functools
import os
from collections.abc import Callable
from importlib import metadata
from pathlib import Path
from typing import Annotated

import typer
import typer.core as typer_core

from bcs.color import ColorMode, build_console, default_streams, resolve_color_enabled
from bcs.commands.doctor import run_doctor
from bcs.commands.inventory import run_inventory
from bcs.commands.stubs import STUB_COMMANDS, StubCommand, run_stub
from bcs.commands.validate import run_validate
from bcs.commands.version import run_version
from bcs.config.loader import ConfigLoader
from bcs.config.preferences import load_preferences
from bcs.context import RuntimeContext
from bcs.exit_codes import ExitCode
from bcs.inventory import collectors
from bcs.inventory.discovery.models import HostDiscoveryAdapters
from bcs.inventory.discovery.orchestrator import HostDiscoveryOrchestrator
from bcs.logging_setup import LogFormat, LogLevelOption, configure_logging, resolve_log_level
from bcs.output import OutputFormat
from bcs.platform.adapters.efi.adapter import read_firmware_boot_configuration
from bcs.platform.adapters.secureboot.adapter import read_secure_boot_status
from bcs.platform.adapters.storage.adapter import read_storage_topology
from bcs.platform.execution import SubprocessCommandRunner
from bcs.plugins import find_plugin, run_plugin, suggest_command
from bcs.ulid import new_ulid

_KNOWN_COMMANDS = ("doctor", "validate", "version", "inventory", *(s.name for s in STUB_COMMANDS))


class BcsGroup(typer_core.TyperGroup):
    """Adds git-style external plugin dispatch (``CLI-009``) on top of
    Typer's normal command resolution. Built-in commands always take
    precedence and are looked up first, by construction: this method
    only runs once Typer's own lookup has already failed.
    """

    def resolve_command(  # type: ignore[override]
        self, ctx: typer.Context, args: list[str]
    ) -> tuple[str | None, typer.core.TyperCommand | None, list[str]]:
        try:
            # The base implementation is typed against the vendored, private
            # click.Command; TyperCommand is its public-facing subtype.
            return super().resolve_command(ctx, args)  # type: ignore[return-value]
        except typer.Exit:
            raise
        except Exception:  # noqa: BLE001 - see module docstring: this is the plugin fallback
            name = args[0] if args else ""
            plugin_path = find_plugin(name)
            if plugin_path is not None:
                exit_code = run_plugin(plugin_path, args[1:], env=_plugin_env(ctx))
                raise SystemExit(exit_code) from None

            suggestion = suggest_command(name, _KNOWN_COMMANDS)
            message = f"bcs: unknown command '{name}'"
            if suggestion:
                message += f" - did you mean '{suggestion}'?"
            typer.echo(message, err=True)
            raise SystemExit(int(ExitCode.PLUGIN_ERROR)) from None


def _plugin_env(ctx: typer.Context) -> dict[str, str]:
    """Cooperating env vars exported to a dispatched plugin (``docs/CLI.md``)."""
    env = dict(os.environ)
    runtime = ctx.obj
    if isinstance(runtime, RuntimeContext):
        env["BCS_VERSION"] = _package_version()
        env["BCS_LOG_LEVEL"] = runtime.log_level.name.lower()
        env["BCS_COLOR"] = "always" if runtime.console.color_system else "never"
        env["BCS_OUTPUT"] = runtime.output.value
        # A plugin can work fine without BCS_CONFIG (e.g. it doesn't need a
        # ClassroomConfig at all); "no config resolved" is a normal case here,
        # not an error worth surfacing.
        with contextlib.suppress(Exception):
            env["BCS_CONFIG"] = str(runtime.config_loader.resolve_path())
    return env


def _package_version() -> str:
    try:
        return metadata.version("bcs")
    except metadata.PackageNotFoundError:  # pragma: no cover - dev checkout w/o install
        return "0.1.0"


def _version_eager_callback(value: bool) -> None:
    if value:
        typer.echo(f"bcs {_package_version()}")
        raise typer.Exit(code=0)


app = typer.Typer(
    cls=BcsGroup,
    add_completion=False,
    pretty_exceptions_enable=False,
    context_settings={"help_option_names": ["-h", "--help"]},
    help="bcs - the Batoi Classroom Suite command-line interface.",
)


@app.callback(invoke_without_command=True)
def main(  # noqa: PLR0913 - global options are inherently numerous; see docs/CLI.md
    ctx: typer.Context,
    config: Annotated[
        Path | None, typer.Option("--config", "-c", help="Path to a ClassroomConfig YAML document.")
    ] = None,
    set_: Annotated[
        list[str], typer.Option("--set", help="Ad hoc config override path=value, repeatable.")
    ] = [],  # noqa: B006 - Typer requires a literal default for multiple options
    output: Annotated[
        OutputFormat, typer.Option("--output", "-o", help="Result format.")
    ] = OutputFormat.TEXT,
    color: Annotated[ColorMode, typer.Option("--color", help="Color mode.")] = ColorMode.AUTO,
    verbose: Annotated[
        int, typer.Option("--verbose", "-v", count=True, help="Increase verbosity (repeatable).")
    ] = 0,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Errors only.")] = False,
    log_level: Annotated[
        LogLevelOption | None,
        typer.Option("--log-level", help="Explicit log level, overrides -v/-q."),
    ] = None,
    log_format: Annotated[
        LogFormat, typer.Option("--log-format", help="Log line format on stderr.")
    ] = LogFormat.TEXT,
    log_file: Annotated[
        Path | None, typer.Option("--log-file", help="Also write logs to this file.")
    ] = None,
    no_input: Annotated[
        bool, typer.Option("--no-input", help="Disable interactive prompts.")
    ] = False,
    yes: Annotated[
        bool, typer.Option("--yes", "-y", help="Pre-confirm destructive operations.")
    ] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Print the plan; skip destructive effects.")
    ] = False,
    timeout: Annotated[
        str | None, typer.Option("--timeout", help="Overall wall-clock budget, e.g. 45m.")
    ] = None,
    _version: Annotated[
        bool,
        typer.Option(
            "--version",
            help="Show the bcs version and exit.",
            is_eager=True,
            callback=_version_eager_callback,
        ),
    ] = False,
) -> None:
    """Build the run's :class:`~bcs.context.RuntimeContext` and store it on
    ``ctx.obj`` before any subcommand runs.
    """
    preferences = load_preferences()
    invocation_id = new_ulid()

    stdout, stderr = default_streams()
    resolved_color = resolve_color_enabled(mode=color, output_format=output, stream=stdout)
    console = build_console(stream=stdout, color_enabled=resolved_color)
    err_console = build_console(
        stream=stderr,
        color_enabled=resolve_color_enabled(mode=color, output_format=output, stream=stderr),
    )

    resolved_level = resolve_log_level(
        explicit=log_level.to_log_level() if log_level is not None else None,
        verbose_count=verbose,
        quiet=quiet,
        warn=stderr,
    )
    configure_logging(
        level=resolved_level,
        log_format=log_format,
        invocation_id=invocation_id,
        command=ctx.invoked_subcommand or "help",
        stream=stderr,
        log_file=log_file,
    )

    effective_config_path = config if config is not None else preferences.default_config
    loader = ConfigLoader(
        explicit_path=effective_config_path,
        set_overrides=list(set_),
        env=dict(os.environ),
    )

    # Built once per invocation and threaded through RuntimeContext, exactly
    # like every other collaborator here - never a module-level singleton or
    # service locator. See docs/PLATFORM_LAYER.md#dependency-injection.
    command_runner = SubprocessCommandRunner()

    # Host Discovery adapters, bound once to the shared command_runner above
    # - see docs/HOST_DISCOVERY_ORCHESTRATOR.md#dependency-injection-strategy---implemented.
    # filesystem/tpm stay unset: no adapter.py exists yet for either domain.
    host_discovery_adapters = HostDiscoveryAdapters(
        efi=functools.partial(read_firmware_boot_configuration, runner=command_runner),
        storage=functools.partial(read_storage_topology, runner=command_runner),
        secure_boot=functools.partial(read_secure_boot_status, runner=command_runner),
        network=collectors.collect_network,
        cpu=collectors.collect_cpu,
        memory=collectors.collect_memory,
    )
    host_discovery_orchestrator = HostDiscoveryOrchestrator(host_discovery_adapters)

    ctx.obj = RuntimeContext(
        invocation_id=invocation_id,
        console=console,
        err_console=err_console,
        output=output,
        log_level=resolved_level,
        log_format=log_format,
        log_file=log_file,
        no_input=no_input,
        yes=yes,
        dry_run=dry_run,
        timeout=timeout,
        config_loader=loader,
        preferences=preferences,
        command_runner=command_runner,
        host_discovery_orchestrator=host_discovery_orchestrator,
    )

    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit(code=0)


@app.command()
def doctor(
    ctx: typer.Context,
    check: Annotated[
        list[str], typer.Option("--check", help="Run only the named check(s), repeatable.")
    ] = [],  # noqa: B006
    strict: Annotated[bool, typer.Option("--strict", help="Treat warnings as failures.")] = False,
) -> None:
    """Diagnose host and configuration readiness."""
    raise typer.Exit(code=run_doctor(ctx.obj, checks=list(check) or None, strict=strict))


@app.command()
def inventory(ctx: typer.Context) -> None:
    """Show the Host Inventory: the single source of truth for this machine."""
    raise typer.Exit(code=run_inventory(ctx.obj))


@app.command()
def validate(
    ctx: typer.Context,
    files: Annotated[
        list[Path] | None, typer.Argument(help="ClassroomConfig file(s); default: resolved config.")
    ] = None,
    strict: Annotated[bool, typer.Option("--strict", help="Treat warnings as failures.")] = False,
) -> None:
    """Validate one or more ClassroomConfig documents."""
    raise typer.Exit(code=run_validate(ctx.obj, files=files, strict=strict))


@app.command(name="version")
def version_command(ctx: typer.Context) -> None:
    """Show version and build information."""
    raise typer.Exit(code=run_version(ctx.obj))


def _make_stub_handler(stub: StubCommand) -> Callable[[typer.Context], None]:
    """Build a command handler bound to one ``stub`` via closure.

    Deliberately takes *only* ``ctx`` in its signature - Typer inspects
    a command function's parameters to build its CLI surface, so
    binding ``stub`` any other way (e.g. a default argument) would leak
    a bogus option into ``bcs <name> --help``.
    """

    def _handler(ctx: typer.Context) -> None:
        raise typer.Exit(code=run_stub(ctx.obj, stub))

    _handler.__name__ = f"stub_{stub.name}"
    return _handler


for _stub_command in STUB_COMMANDS:
    app.command(
        name=_stub_command.name,
        help=f"(not implemented in this phase) owned by {_stub_command.owner}.",
    )(_make_stub_handler(_stub_command))


__all__ = ["BcsGroup", "app"]
