"""``bcs version`` - see ``docs/CLI.md#bcs-version``.

Always exits ``0`` (``ExitCode.SUCCESS``): version info is printed even
for an incompatible or unresolvable config - ``loadedConfig`` reflects
that instead of the command failing.
"""

from __future__ import annotations

import os
from importlib import metadata
from typing import Any

from bcs.config.loader import SUPPORTED_API_VERSIONS
from bcs.context import RuntimeContext
from bcs.errors import ConfigInvalidError
from bcs.output import OutputFormat, print_structured_result

_FALLBACK_VERSION = "0.1.0"


def _package_version() -> str:
    try:
        return metadata.version("bcs")
    except metadata.PackageNotFoundError:  # pragma: no cover - dev checkout w/o install
        return _FALLBACK_VERSION


def _loaded_config_info(runtime: RuntimeContext) -> dict[str, Any] | None:
    try:
        path = runtime.config_loader.resolve_path()
    except Exception:  # noqa: BLE001 - "no config resolvable" is a normal case here
        return None

    try:
        config = runtime.config_loader.load(path)
    except ConfigInvalidError:
        return {"path": str(path), "apiVersion": None, "compatible": False}

    return {
        "path": str(path),
        "apiVersion": config.api_version,
        "compatible": config.api_version in SUPPORTED_API_VERSIONS,
    }


def run_version(runtime: RuntimeContext) -> int:
    """Implement ``bcs version``. Returns the process exit code."""
    version = _package_version()
    commit = os.environ.get("BCS_BUILD_COMMIT")
    build_date = os.environ.get("BCS_BUILD_DATE")
    supported_api_versions = sorted(SUPPORTED_API_VERSIONS)
    loaded_config = _loaded_config_info(runtime)

    payload: dict[str, Any] = {
        "version": version,
        "commit": commit,
        "buildDate": build_date,
        "supportedConfigApiVersions": supported_api_versions,
        "loadedConfig": loaded_config,
    }

    if runtime.output is OutputFormat.TEXT:
        runtime.console.print(f"[bold]bcs[/bold] {version}")
        if commit:
            runtime.console.print(f"  commit: {commit}")
        if build_date:
            runtime.console.print(f"  build date: {build_date}")
        runtime.console.print(
            "  supported config apiVersion(s): " + ", ".join(supported_api_versions)
        )
        if loaded_config is None:
            runtime.console.print("  loaded config: [dim]none resolved[/dim]")
        else:
            compatible = "yes" if loaded_config["compatible"] else "[red]no[/red]"
            runtime.console.print(
                f"  loaded config: {loaded_config['path']} "
                f"(apiVersion={loaded_config['apiVersion']}, compatible={compatible})"
            )
    else:
        print_structured_result(runtime.console, runtime.output, payload)

    return 0


__all__ = ["run_version"]
