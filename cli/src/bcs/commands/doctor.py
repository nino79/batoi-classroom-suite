"""``bcs doctor`` - see ``docs/CLI.md#bcs-doctor``.

Diagnoses host/tooling/config readiness. Checks are independent of one
another and of whether a ClassroomConfig resolves at all - only the
``config`` check itself depends on one being present, and its absence
is a ``warn``, not a hard failure, since ``doctor`` is meant to be
useful before a classroom has been configured yet.

``firmware``, ``esp``, ``storage``, ``usb-storage``, ``network``, and
``tooling`` are pass/fail *evaluations* of facts collected by the Host
Inventory subsystem (:mod:`bcs.inventory`) - they no longer probe the
host directly, so ``bcs doctor`` and ``bcs inventory`` can never
disagree about what the machine actually looks like for those checks.
``permissions`` (a fact about the current *process*, not the host) and
``config`` (a ClassroomConfig concern) are doctor-specific and stay
outside the inventory subsystem's scope.

``secure-boot`` (Beta M4) is the one exception: it calls the Secure
Boot Platform Adapter directly, via ``runtime.command_runner``, rather
than the Host Inventory subsystem - deliberately, per ADR-0011's own
"Alternatives Considered" rejecting a full
``HostDiscoveryOrchestrator.discover()`` sweep for ``bcs doctor`` (see
:func:`_check_secure_boot`'s own docstring). ``collect_firmware()`` is
still used for the cheap UEFI-presence gate only, matching
``_check_firmware()``'s own mechanism.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from bcs.config.validator import validate_document
from bcs.context import RuntimeContext
from bcs.errors import PreconditionFailedError, UsageError
from bcs.inventory.collectors import (
    collect_efi_system_partition,
    collect_firmware,
    collect_network,
    collect_storage,
    collect_tooling,
    collect_usb_storage,
)
from bcs.output import OutputFormat, print_structured_result
from bcs.platform.adapters.secureboot.adapter import read_secure_boot_status
from bcs.platform.adapters.secureboot.models import SecureBootState as PlatformSecureBootState
from bcs.platform.errors import PlatformError

CheckStatus = Literal["ok", "warn", "fail", "skip"]


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: CheckStatus
    message: str


def _check_firmware() -> CheckResult:
    firmware = collect_firmware()
    if firmware.uefi:
        return CheckResult("firmware", "ok", "UEFI firmware detected (PLAT-003)")
    return CheckResult("firmware", "fail", "UEFI firmware not detected (PLAT-003)")


def _check_secure_boot(runtime: RuntimeContext) -> CheckResult:
    """Evaluate Secure Boot state via a direct call to the Secure Boot
    Platform Adapter (Beta M4), sharing ``runtime.command_runner`` with
    every other Platform Layer collaborator.

    Deliberately **not** ``runtime.host_discovery_orchestrator.discover()``:
    per ADR-0011's own "Alternatives Considered" (the full-sweep
    orchestrator was rejected for ``bcs doctor`` specifically, to
    preserve each check's independence - one check must never pay for,
    or be blocked by, an unrelated domain's adapter call). This mirrors
    every other check in this module, which reads exactly one collector/
    adapter directly rather than aggregating through
    ``collect_host_inventory()``.
    """
    if not collect_firmware().uefi:
        return CheckResult("secure-boot", "skip", "not applicable: not running under UEFI")

    try:
        status = read_secure_boot_status(runtime.command_runner)
    except PlatformError as exc:
        return CheckResult(
            "secure-boot",
            "warn",
            f"Secure Boot state could not be determined ({type(exc).__name__}: {exc}) (PLAT-004)",
        )

    if status.state is PlatformSecureBootState.ENABLED:
        return CheckResult("secure-boot", "ok", "Secure Boot is enabled (PLAT-004)")
    if status.state is PlatformSecureBootState.DISABLED:
        return CheckResult("secure-boot", "warn", "Secure Boot is disabled (PLAT-004)")
    return CheckResult(
        "secure-boot",
        "warn",
        f"Secure Boot state could not be determined ({status.state.value}) (PLAT-004)",
    )


def _check_storage() -> CheckResult:
    devices = collect_storage()
    if devices:
        names = ", ".join(device.name for device in devices)
        return CheckResult("storage", "ok", f"NVMe device(s) found: {names}")
    return CheckResult("storage", "fail", "no NVMe device found (PLAT-005)")


def _check_esp() -> CheckResult:
    esp = collect_efi_system_partition()
    if not esp.present:
        return CheckResult("esp", "fail", "no EFI System Partition found (BLD-004/DEP-003)")
    if not esp.mounted:
        return CheckResult("esp", "warn", "EFI System Partition present but not mounted")
    return CheckResult("esp", "ok", f"EFI System Partition mounted at {esp.mount_point}")


def _check_usb_storage() -> CheckResult:
    devices = collect_usb_storage()
    if not devices:
        return CheckResult("usb-storage", "skip", "no USB storage devices detected")
    names = ", ".join(device.name for device in devices)
    return CheckResult("usb-storage", "ok", f"USB storage device(s) found: {names}")


def _check_network() -> CheckResult:
    interfaces = [iface for iface in collect_network() if not iface.is_loopback]
    if not interfaces:
        return CheckResult("network", "skip", "no non-loopback network interfaces detected")
    up = [iface for iface in interfaces if iface.is_up]
    if up:
        names = ", ".join(iface.name for iface in up)
        return CheckResult(
            "network",
            "ok",
            f"{len(up)} interface(s) up ({names}); "
            "PXE/multicast reachability itself remains a placeholder (PLAT-007)",
        )
    return CheckResult(
        "network", "warn", f"{len(interfaces)} interface(s) detected but none are up (PLAT-007)"
    )


def _check_tooling() -> CheckResult:
    tools = collect_tooling()
    missing = [tool.name for tool in tools if not tool.found]
    if not missing:
        return CheckResult("tooling", "ok", "all expected tools found on PATH")
    return CheckResult("tooling", "fail", f"missing on PATH: {', '.join(missing)}")


def _check_permissions() -> CheckResult:
    geteuid = getattr(os, "geteuid", None)
    if geteuid is None:
        return CheckResult("permissions", "skip", "not applicable on this platform")
    if geteuid() == 0:
        return CheckResult("permissions", "ok", "running as root")
    return CheckResult("permissions", "warn", "not running as root; some operations may fail")


def _check_config(runtime: RuntimeContext) -> CheckResult:
    try:
        path = runtime.config_loader.resolve_path()
    except UsageError:
        return CheckResult("config", "warn", "no ClassroomConfig resolved (see --config)")

    report = validate_document(runtime.config_loader, path)
    if report.errors:
        message = f"{path} failed validation ({len(report.errors)} error(s))"
        return CheckResult("config", "fail", message)
    if report.warnings:
        message = f"{path} is valid with {len(report.warnings)} warning(s)"
        return CheckResult("config", "warn", message)
    return CheckResult("config", "ok", f"{path} is valid")


_ALL_CHECKS: dict[str, Callable[[RuntimeContext], CheckResult]] = {
    "firmware": lambda _runtime: _check_firmware(),
    "secure-boot": _check_secure_boot,
    "esp": lambda _runtime: _check_esp(),
    "storage": lambda _runtime: _check_storage(),
    "usb-storage": lambda _runtime: _check_usb_storage(),
    "network": lambda _runtime: _check_network(),
    "tooling": lambda _runtime: _check_tooling(),
    "permissions": lambda _runtime: _check_permissions(),
    "config": _check_config,
}

_STATUS_STYLE = {"ok": "green", "warn": "yellow", "fail": "red", "skip": "dim"}
_STATUS_LABEL = {"ok": "OK", "warn": "WARN", "fail": "FAIL", "skip": "SKIP"}


def run_doctor(
    runtime: RuntimeContext,
    *,
    checks: list[str] | None = None,
    strict: bool = False,
) -> int:
    """Implement ``bcs doctor``. Returns the process exit code."""
    selected = checks or list(_ALL_CHECKS)
    unknown = [name for name in selected if name not in _ALL_CHECKS]
    if unknown:
        msg = f"unknown check(s): {', '.join(unknown)}; known checks: {', '.join(_ALL_CHECKS)}"
        raise UsageError(msg)

    results = [_ALL_CHECKS[name](runtime) for name in selected]

    if runtime.output is OutputFormat.TEXT:
        for result in results:
            style = _STATUS_STYLE[result.status]
            label = _STATUS_LABEL[result.status].ljust(5)
            runtime.console.print(
                f"[{style}][{label}][/{style}] {result.name:<12} {result.message}"
            )
        counts = {status: sum(1 for r in results if r.status == status) for status in _STATUS_STYLE}
        summary = ", ".join(
            f"{counts[status]} {status}"
            for status in ("ok", "warn", "fail", "skip")
            if counts[status]
        )
        runtime.console.print(summary)
    else:
        payload = {
            "checks": [{"name": r.name, "status": r.status, "message": r.message} for r in results],
            "summary": {
                status: sum(1 for r in results if r.status == status)
                for status in ("ok", "warn", "fail", "skip")
            },
        }
        print_structured_result(runtime.console, runtime.output, payload)

    any_fail = any(r.status == "fail" for r in results)
    any_warn = any(r.status == "warn" for r in results)
    if any_fail or (strict and any_warn):
        raise PreconditionFailedError("one or more doctor checks did not pass")
    return 0


__all__ = ["CheckResult", "run_doctor"]
