from __future__ import annotations

import io
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml
from rich.console import Console

# The captured-tool-output fixture corpus root lives in fixture_utils.FIXTURES_ROOT
# (tests/fixtures/ - see its README.md); load fixtures through that module's
# helpers, not with ad hoc paths from here.


@pytest.fixture
def capsys_console() -> Console:
    """A Rich Console writing to an in-memory buffer, colors disabled."""
    return Console(
        file=io.StringIO(), no_color=True, force_terminal=False, width=120, soft_wrap=True
    )


@pytest.fixture
def valid_config_data() -> dict[str, Any]:
    """A minimal-but-complete ClassroomConfig document as a plain dict."""
    return {
        "apiVersion": "bcs/v1alpha1",
        "kind": "ClassroomConfig",
        "metadata": {"name": "test-classroom"},
        "spec": {
            "project": {"displayName": "Test Classroom", "centre": "Test Centre"},
            "bootManager": {
                "menu": {
                    "defaultEntry": "normal-boot",
                    "entries": [
                        {
                            "id": "normal-boot",
                            "label": {"ca_ES": "Inicia", "es_ES": "Iniciar"},
                            "action": "boot-installed-os",
                        },
                        {
                            "id": "maintenance",
                            "label": {"ca_ES": "Manteniment", "es_ES": "Mantenimiento"},
                            "action": "request-deploy-maintenance",
                        },
                    ],
                }
            },
            "builder": {
                "baseImage": {"distro": "lliurex", "baseDistribution": "ubuntu"},
                "partitioning": {},
            },
            "packages": {"base": ["lliurex-desktop"]},
            "deploy": {},
            "network": {"addressing": {"mode": "dhcp"}},
            "localization": {},
            "security": {"secureBoot": {"mode": "enforce"}},
        },
    }


@pytest.fixture
def valid_config_path(tmp_path: Path, valid_config_data: dict[str, Any]) -> Path:
    path = tmp_path / "classroom.yaml"
    path.write_text(yaml.safe_dump(valid_config_data), encoding="utf-8")
    return path


@pytest.fixture
def real_example_config_path() -> Path:
    """The actual config/examples/default.yaml from the repository."""
    path = Path(__file__).parents[2] / "config" / "examples" / "default.yaml"
    assert path.is_file(), f"expected repository fixture at {path}"
    return path


@pytest.fixture
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point HOME/XDG_CONFIG_HOME somewhere empty so tests never read a
    real developer's ``~/.config/bcs/cli.yaml``.
    """
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    monkeypatch.delenv("BCS_CONFIG", raising=False)
    return home


@pytest.fixture
def make_runtime_context():
    """Factory for a :class:`~bcs.context.RuntimeContext` wired to
    in-memory consoles, for testing command functions directly without
    going through the full Typer/Click CLI layer.
    """
    from bcs.config.loader import ConfigLoader
    from bcs.config.preferences import CliPreferences
    from bcs.context import RuntimeContext
    from bcs.inventory.discovery.models import HostDiscoveryAdapters
    from bcs.inventory.discovery.orchestrator import HostDiscoveryOrchestrator
    from bcs.logging_setup import LogFormat, LogLevel
    from bcs.output import OutputFormat
    from bcs.platform.execution import CommandRunner, SubprocessCommandRunner

    def _factory(  # noqa: PLR0913 - a test factory's whole point is exposing every collaborator
        *,
        config_path: Path | None = None,
        output: OutputFormat = OutputFormat.TEXT,
        set_overrides: list[str] | None = None,
        env: dict[str, str] | None = None,
        command_runner: CommandRunner | None = None,
        host_discovery_orchestrator: HostDiscoveryOrchestrator | None = None,
    ) -> RuntimeContext:
        console = Console(
            file=io.StringIO(), no_color=True, force_terminal=False, width=120, soft_wrap=True
        )
        err_console = Console(
            file=io.StringIO(), no_color=True, force_terminal=False, width=120, soft_wrap=True
        )
        loader = ConfigLoader(
            explicit_path=config_path,
            set_overrides=set_overrides or [],
            env=env if env is not None else {},
        )
        return RuntimeContext(
            invocation_id="01TESTINVOCATIONID0000000",
            console=console,
            err_console=err_console,
            output=output,
            log_level=LogLevel.INFO,
            log_format=LogFormat.TEXT,
            log_file=None,
            no_input=False,
            yes=False,
            dry_run=False,
            timeout=None,
            config_loader=loader,
            preferences=CliPreferences(),
            command_runner=(
                command_runner if command_runner is not None else SubprocessCommandRunner()
            ),
            host_discovery_orchestrator=(
                host_discovery_orchestrator
                if host_discovery_orchestrator is not None
                else HostDiscoveryOrchestrator(HostDiscoveryAdapters())
            ),
        )

    return _factory


@pytest.fixture
def fake_plugin(tmp_path: Path) -> Path:
    """A directory on a fake PATH containing an executable ``bcs-hello``."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    is_windows = shutil.which("cmd") is not None and Path("C:/").exists()
    if is_windows:
        script = bin_dir / "bcs-hello.cmd"
        script.write_text("@echo off\r\necho hello from plugin\r\nexit /b 0\r\n")
    else:
        script = bin_dir / "bcs-hello"
        script.write_text("#!/bin/sh\necho 'hello from plugin'\nexit 0\n")
        script.chmod(0o755)
    return bin_dir
