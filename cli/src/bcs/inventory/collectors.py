"""Host inventory collectors.

Each function here probes exactly one aspect of the current machine
and returns a single immutable model from :mod:`bcs.inventory.models`.
Collectors **never print** - formatting and printing are the CLI's job
(``bcs.commands.inventory``), per the Host Inventory subsystem's
contract (``docs/CLI.md``'s "stdout is data" rule, generalized here to
"a collector's return value is data").

Every collector is defensive: a missing file, an unavailable syscall,
or an unrecognized platform produces an "unknown"/empty value in the
returned model, never an exception - a partial inventory is always
preferable to a crashed one. This mirrors the same philosophy already
established for ``bcs doctor``'s checks (see ``bcs.commands.doctor``),
which now build on these same collectors instead of duplicating them.

These collectors are Linux-oriented placeholders (``/sys``, ``/proc``,
``/dev``), matching BCS's fixed target platform (``PLAT-001``-``PLAT-007``:
LliureX/Ubuntu, UEFI, NVMe) - they degrade gracefully, not silently
fake data, on any other platform.
"""

from __future__ import annotations

import os
import platform
import shutil
from pathlib import Path

from bcs.inventory.models import (
    CpuInfo,
    FirmwareInfo,
    HostIdentity,
    MemoryInfo,
    NetworkInterface,
    OperatingSystemInfo,
    SecureBootState,
    StorageDevice,
    ToolStatus,
)

#: External tools Deploy/Builder will eventually shell out to.
EXPECTED_TOOLS = ("clonezilla", "partclone")

_SYS_FIRMWARE_EFI = Path("/sys/firmware/efi")
_SYS_FIRMWARE_EFIVARS = Path("/sys/firmware/efi/efivars")
_SYS_CLASS_NET = Path("/sys/class/net")
_SYS_CLASS_DMI_PRODUCT_UUID = Path("/sys/class/dmi/id/product_uuid")
_DEV = Path("/dev")
_PROC_MEMINFO = Path("/proc/meminfo")
_PROC_CPUINFO = Path("/proc/cpuinfo")
_ETC_OS_RELEASE = Path("/etc/os-release")
_NULL_MAC = "00:00:00:00:00:00"


def _read_text(path: Path) -> str | None:
    """Read a small pseudo-file, returning ``None`` on any failure."""
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return text or None


def collect_firmware() -> FirmwareInfo:
    """Probe UEFI/Secure Boot state - see ``PLAT-003``, ``PLAT-004``."""
    if not _SYS_FIRMWARE_EFI.is_dir():
        return FirmwareInfo(uefi=False, secure_boot=SecureBootState.UNSUPPORTED)
    return FirmwareInfo(uefi=True, secure_boot=_read_secure_boot_state())


def _read_secure_boot_state() -> SecureBootState:
    if not _SYS_FIRMWARE_EFIVARS.is_dir():
        return SecureBootState.UNKNOWN
    # Parsing the SecureBoot-<GUID> EFI variable's actual byte value is a
    # placeholder for future work; presence of efivars only confirms the
    # firmware exposes UEFI variables at all, not the Secure Boot toggle.
    return SecureBootState.UNKNOWN


def collect_storage() -> list[StorageDevice]:
    """Enumerate NVMe block devices - see ``PLAT-005``."""
    if not _DEV.is_dir():
        return []
    return [
        StorageDevice(name=entry.name, path=str(entry), is_nvme=True)
        for entry in sorted(_DEV.glob("nvme[0-9]n[0-9]"))
    ]


def collect_network() -> list[NetworkInterface]:
    """Enumerate network interfaces via ``/sys/class/net``.

    IP address enumeration is a known placeholder gap (empty
    ``ipAddresses``): pure-stdlib, per-interface IP discovery isn't
    portable without either a new dependency or shelling out to
    ``ip``/``ifconfig``, neither of which is in scope for this pass.
    """
    if not _SYS_CLASS_NET.is_dir():
        return []
    interfaces = []
    for iface_dir in sorted(_SYS_CLASS_NET.iterdir()):
        name = iface_dir.name
        operstate = _read_text(iface_dir / "operstate")
        interfaces.append(
            NetworkInterface(
                name=name,
                mac_address=_read_text(iface_dir / "address"),
                ip_addresses=[],
                is_up=(operstate == "up"),
                is_loopback=(name == "lo"),
            )
        )
    return interfaces


def collect_identity() -> HostIdentity:
    """Collect candidate stable machine identifiers.

    See :class:`bcs.inventory.models.HostIdentity` for why this exists.
    """
    return HostIdentity(
        primary_mac_address=_primary_mac_address(),
        dmi_product_uuid=_read_text(_SYS_CLASS_DMI_PRODUCT_UUID),
    )


def _primary_mac_address() -> str | None:
    if not _SYS_CLASS_NET.is_dir():
        return None
    for iface_dir in sorted(_SYS_CLASS_NET.iterdir()):
        if iface_dir.name == "lo":
            continue
        mac = _read_text(iface_dir / "address")
        if mac and mac.lower() != _NULL_MAC:
            return mac
    return None


def collect_operating_system() -> OperatingSystemInfo:
    """Identify the running OS - see ``PLAT-001``, ``PLAT-002``."""
    name = _read_os_release_pretty_name() or platform.system() or "unknown"
    return OperatingSystemInfo(
        name=name,
        version=platform.version() or None,
        kernel=platform.release() or None,
        architecture=platform.machine() or "unknown",
    )


def _read_os_release_pretty_name() -> str | None:
    text = _read_text(_ETC_OS_RELEASE)
    if text is None:
        return None
    for line in text.splitlines():
        if line.startswith("PRETTY_NAME="):
            return line.split("=", 1)[1].strip().strip('"') or None
    return None


def collect_memory() -> MemoryInfo:
    """Read total/available memory from ``/proc/meminfo``, in bytes."""
    text = _read_text(_PROC_MEMINFO)
    if text is None:
        return MemoryInfo()
    total = available = None
    for line in text.splitlines():
        if line.startswith("MemTotal:"):
            total = _parse_meminfo_kb_line(line)
        elif line.startswith("MemAvailable:"):
            available = _parse_meminfo_kb_line(line)
    return MemoryInfo(total_bytes=total, available_bytes=available)


def _parse_meminfo_kb_line(line: str) -> int | None:
    parts = line.split()
    if len(parts) >= 2 and parts[1].isdigit():  # noqa: PLR2004 - "kB" is always parts[1]
        return int(parts[1]) * 1024
    return None


def collect_cpu() -> CpuInfo:
    """Collect CPU architecture, model name, and logical core count."""
    return CpuInfo(
        architecture=platform.machine() or "unknown",
        model=_read_cpu_model(),
        logical_cores=os.cpu_count(),
    )


def _read_cpu_model() -> str | None:
    text = _read_text(_PROC_CPUINFO)
    if text is None:
        return None
    for line in text.splitlines():
        if line.lower().startswith("model name"):
            _, _, value = line.partition(":")
            return value.strip() or None
    return None


def collect_tooling(tools: tuple[str, ...] = EXPECTED_TOOLS) -> list[ToolStatus]:
    """Check which expected external tools are present on ``PATH``."""
    return [
        ToolStatus(name=name, found=(path := shutil.which(name)) is not None, path=path)
        for name in tools
    ]


__all__ = [
    "EXPECTED_TOOLS",
    "collect_cpu",
    "collect_firmware",
    "collect_identity",
    "collect_memory",
    "collect_network",
    "collect_operating_system",
    "collect_storage",
    "collect_tooling",
]
