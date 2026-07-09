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
import re
import shutil
from pathlib import Path

from bcs.inventory.models import (
    CpuInfo,
    EfiSystemPartition,
    FirmwareInfo,
    HostIdentity,
    MemoryInfo,
    NetworkInterface,
    OperatingSystemInfo,
    SecureBootState,
    StorageDevice,
    ToolStatus,
    UsbStorageDevice,
)

#: External tools Deploy/Builder will eventually shell out to.
EXPECTED_TOOLS = ("clonezilla", "partclone")

_SYS_FIRMWARE_EFI = Path("/sys/firmware/efi")
_SYS_FIRMWARE_EFIVARS = Path("/sys/firmware/efi/efivars")
_SYS_CLASS_NET = Path("/sys/class/net")
_SYS_CLASS_DMI_PRODUCT_UUID = Path("/sys/class/dmi/id/product_uuid")
_SYS_BLOCK = Path("/sys/block")
_DEV = Path("/dev")
_DEV_DISK_BY_UUID = Path("/dev/disk/by-uuid")
_PROC_MEMINFO = Path("/proc/meminfo")
_PROC_CPUINFO = Path("/proc/cpuinfo")
_PROC_MOUNTS = Path("/proc/mounts")
_ETC_OS_RELEASE = Path("/etc/os-release")
_NULL_MAC = "00:00:00:00:00:00"

#: Ubuntu/LliureX (``PLAT-001``/``PLAT-002``) conventionally mount the ESP
#: here. A non-standard ESP mount point is a known collector limitation
#: (see ``collect_efi_system_partition``), not a guess at other conventions.
_ESP_MOUNT_POINT = "/boot/efi"

_NVME_PARTITION_RE = re.compile(r"^(?P<disk>/dev/nvme\d+n\d+)p\d+$")
_GENERIC_PARTITION_RE = re.compile(r"^(?P<disk>/dev/[a-zA-Z]+)\d+$")


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
    """Enumerate NVMe block devices - see ``PLAT-005``.

    .. deprecated::
       Legacy fallback. The Storage Adapter
       (``bcs.platform.adapters.storage.adapter.read_storage_topology``) is
       the primary source via ``HostDiscoverySnapshot.storage_topology``.
       This collector remains as a fallback when the adapter slot is unset
       or fails, and for direct use by ``bcs doctor``'s ``_check_storage``.
       Scheduled for removal once ``bcs doctor`` migrates to adapter data.
    """
    if not _DEV.is_dir():
        return []
    return [
        StorageDevice(name=entry.name, path=str(entry), is_nvme=True)
        for entry in sorted(_DEV.glob("nvme[0-9]n[0-9]"))
    ]


def collect_efi_system_partition() -> EfiSystemPartition:
    """Probe the EFI System Partition - see ``BLD-004``, ``DEP-003``, ``CLI-016``.

    Looks only at ``/boot/efi`` (see ``_ESP_MOUNT_POINT``), the Ubuntu/
    LliureX convention (``PLAT-001``/``PLAT-002``). A machine with a
    non-standard ESP mount point is reported as ``present=False`` - a
    documented collector limitation, not a guess at other conventions.
    """
    mount = _read_esp_mount()
    if mount is None:
        return EfiSystemPartition(present=False, mounted=False)
    partition, filesystem = mount
    total, free = _partition_usage(_ESP_MOUNT_POINT)
    return EfiSystemPartition(
        present=True,
        device=_parent_disk(partition),
        partition=partition,
        uuid=_partition_uuid(partition),
        filesystem=filesystem,
        mount_point=_ESP_MOUNT_POINT,
        size_bytes=total,
        free_bytes=free,
        mounted=True,
    )


def _read_esp_mount() -> tuple[str, str] | None:
    """Return ``(source_device, filesystem)`` for the last ``/proc/mounts``
    entry at ``_ESP_MOUNT_POINT``, or ``None`` if nothing is mounted there.

    The *last* matching line wins, mirroring how the kernel's mount table
    itself reflects the most recent mount at a given point.
    """
    text = _read_text(_PROC_MOUNTS)
    if text is None:
        return None
    match: tuple[str, str] | None = None
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[1] == _ESP_MOUNT_POINT:  # noqa: PLR2004
            match = (parts[0], parts[2])
    return match


def _parent_disk(partition: str) -> str | None:
    """Derive a whole-disk path (e.g. ``/dev/nvme0n1``) from a partition
    path (e.g. ``/dev/nvme0n1p1``), using standard Linux device naming.
    """
    for pattern in (_NVME_PARTITION_RE, _GENERIC_PARTITION_RE):
        match = pattern.match(partition)
        if match:
            return match.group("disk")
    return None


def _partition_uuid(partition: str) -> str | None:
    """Look up ``partition``'s filesystem UUID via ``/dev/disk/by-uuid``."""
    if not _DEV_DISK_BY_UUID.is_dir():
        return None
    try:
        target = os.path.realpath(partition)
    except OSError:
        return None
    for entry in sorted(_DEV_DISK_BY_UUID.iterdir()):
        if os.path.realpath(entry) == target:
            return entry.name
    return None


def _partition_usage(mount_point: str) -> tuple[int | None, int | None]:
    """Return ``(total_bytes, free_bytes)`` for a mounted path, or
    ``(None, None)`` if unavailable (e.g. non-POSIX platform, race with
    an unmount between detection and this call).
    """
    statvfs = getattr(os, "statvfs", None)
    if statvfs is None:
        return None, None
    try:
        stats = statvfs(mount_point)
    except OSError:
        return None, None
    return stats.f_frsize * stats.f_blocks, stats.f_frsize * stats.f_bavail


def collect_usb_storage() -> list[UsbStorageDevice]:
    """Enumerate USB-attached storage devices - see ``CLI-016``.

    Scope is deliberately narrow: only USB-attached storage suitable for
    booting or deployment (e.g. a recovery USB drive) - see ADR-0008's
    amendment. Devices are identified by (a) the ``removable`` sysfs
    attribute and (b) a ``usb*`` segment in the resolved sysfs device
    path, the standard Linux convention for USB-attached block devices.
    Internal NVMe storage is covered by :func:`collect_storage`, not here.
    """
    if not _SYS_BLOCK.is_dir():
        return []
    return [
        _read_usb_storage_device(block_dir)
        for block_dir in sorted(_SYS_BLOCK.iterdir())
        if _is_usb_removable(block_dir)
    ]


def _is_usb_removable(block_dir: Path) -> bool:
    if _read_text(block_dir / "removable") != "1":
        return False
    try:
        real_path = os.path.realpath(block_dir)
    except OSError:
        return False
    return any(part.startswith("usb") for part in Path(real_path).parts)


def _read_usb_storage_device(block_dir: Path) -> UsbStorageDevice:
    name = block_dir.name
    size_text = _read_text(block_dir / "size")
    size_bytes = int(size_text) * 512 if size_text and size_text.isdigit() else None
    mount_point = _find_mounted_partition(name)
    return UsbStorageDevice(
        name=name,
        path=f"/dev/{name}",
        vendor=_read_text(block_dir / "device" / "vendor"),
        model=_read_text(block_dir / "device" / "model"),
        size_bytes=size_bytes,
        mounted=mount_point is not None,
        mount_point=mount_point,
    )


def _find_mounted_partition(disk_name: str) -> str | None:
    """Return the mount point of the first ``/proc/mounts`` entry whose
    device is ``disk_name`` itself or one of its partitions, or ``None``.
    """
    text = _read_text(_PROC_MOUNTS)
    if text is None:
        return None
    prefix = f"/dev/{disk_name}"
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0].startswith(prefix):  # noqa: PLR2004
            return parts[1]
    return None


def collect_network() -> list[NetworkInterface]:
    """Enumerate network interfaces via ``/sys/class/net``.

    IP address enumeration is a known placeholder gap (empty
    ``ipAddresses``): pure-stdlib, per-interface IP discovery isn't
    portable without either a new dependency or shelling out to
    ``ip``/``ifconfig``, neither of which is in scope for this pass.

    .. deprecated::
       Legacy fallback. The Network Adapter
       (``bcs.platform.adapters.network.adapter.read_network_interfaces``) is
       the primary source via ``HostDiscoverySnapshot.network_interfaces``.
       This collector remains as a fallback when the adapter slot is unset
       or fails. Scheduled for removal once the orchestrator guarantees
       adapter availability.
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
    "collect_efi_system_partition",
    "collect_firmware",
    "collect_identity",
    "collect_memory",
    "collect_network",
    "collect_operating_system",
    "collect_storage",
    "collect_tooling",
    "collect_usb_storage",
]
