from __future__ import annotations

import pytest

from bcs.inventory import collectors, service
from bcs.inventory.discovery.models import HostDiscoveryAdapters
from bcs.inventory.discovery.orchestrator import HostDiscoveryOrchestrator
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
from bcs.platform.errors import PlatformError


class _CountingAdapter[T]:
    """A fake adapter callable that records how many times it was
    called, and either returns ``value`` or raises ``error`` (never
    both, on any single call) each time it is invoked. Mirrors the
    same fake used in ``test_inventory_discovery_orchestrator.py``.
    """

    def __init__(self, value: T, *, error: Exception | None = None) -> None:
        self._value = value
        self._error = error
        self.call_count = 0

    def __call__(self) -> T:
        self.call_count += 1
        if self._error is not None:
            raise self._error
        return self._value


def test_collect_host_inventory_assembles_all_sections(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        collectors, "collect_identity", lambda: HostIdentity(primaryMacAddress="aa:bb:cc:dd:ee:ff")
    )
    monkeypatch.setattr(
        collectors,
        "collect_firmware",
        lambda: FirmwareInfo(uefi=True, secureBoot=SecureBootState.ENABLED),
    )
    monkeypatch.setattr(
        collectors,
        "collect_operating_system",
        lambda: OperatingSystemInfo(name="LliureX", architecture="x86_64"),
    )
    monkeypatch.setattr(
        collectors, "collect_cpu", lambda: CpuInfo(architecture="x86_64", logicalCores=8)
    )
    monkeypatch.setattr(collectors, "collect_memory", lambda: MemoryInfo(totalBytes=1024))
    monkeypatch.setattr(
        collectors,
        "collect_efi_system_partition",
        lambda: EfiSystemPartition(present=True, mountPoint="/boot/efi", mounted=True),
    )
    monkeypatch.setattr(
        collectors,
        "collect_storage",
        lambda: [StorageDevice(name="nvme0n1", path="/dev/nvme0n1", isNvme=True)],
    )
    monkeypatch.setattr(
        collectors,
        "collect_usb_storage",
        lambda: [UsbStorageDevice(name="sdb", path="/dev/sdb", mounted=False)],
    )
    monkeypatch.setattr(
        collectors,
        "collect_network",
        lambda: [NetworkInterface(name="eth0", isUp=True, isLoopback=False)],
    )
    monkeypatch.setattr(
        collectors,
        "collect_tooling",
        lambda: [ToolStatus(name="clonezilla", found=True, path="/usr/bin/clonezilla")],
    )

    inventory = service.collect_host_inventory()

    assert inventory.identity.primary_mac_address == "aa:bb:cc:dd:ee:ff"
    assert inventory.firmware.uefi is True
    assert inventory.operating_system.name == "LliureX"
    assert inventory.cpu.logical_cores == 8
    assert inventory.memory.total_bytes == 1024
    assert inventory.efi_system_partition.present is True
    assert inventory.efi_system_partition.mount_point == "/boot/efi"
    assert len(inventory.storage) == 1
    assert inventory.storage[0].name == "nvme0n1"
    assert len(inventory.usb_storage) == 1
    assert inventory.usb_storage[0].name == "sdb"
    assert len(inventory.network) == 1
    assert inventory.network[0].name == "eth0"
    assert len(inventory.tooling) == 1
    assert inventory.tooling[0].name == "clonezilla"
    assert inventory.collected_at is not None


def test_collect_host_inventory_runs_on_real_host_without_crashing() -> None:
    """No mocking - the real collectors must degrade gracefully on
    whatever platform the test suite happens to run on.
    """
    inventory = service.collect_host_inventory()
    assert inventory.schema_version == "bcs-inventory/v1alpha1"


# ---------------------------------------------------------------------------
# Host Discovery integration
# (docs/HOST_DISCOVERY_ORCHESTRATOR.md#relationship-to-host-inventory---implemented)
# ---------------------------------------------------------------------------


def _patch_non_discovery_collectors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch every collector *other than* cpu/memory/network - the
    seven sections that must be unaffected by whether an orchestrator
    is given, per this module's own docstring.
    """
    monkeypatch.setattr(
        collectors, "collect_identity", lambda: HostIdentity(primaryMacAddress="aa:bb:cc:dd:ee:ff")
    )
    monkeypatch.setattr(
        collectors,
        "collect_firmware",
        lambda: FirmwareInfo(uefi=True, secureBoot=SecureBootState.ENABLED),
    )
    monkeypatch.setattr(
        collectors,
        "collect_operating_system",
        lambda: OperatingSystemInfo(name="LliureX", architecture="x86_64"),
    )
    monkeypatch.setattr(
        collectors,
        "collect_efi_system_partition",
        lambda: EfiSystemPartition(present=True, mountPoint="/boot/efi", mounted=True),
    )
    monkeypatch.setattr(
        collectors,
        "collect_storage",
        lambda: [StorageDevice(name="nvme0n1", path="/dev/nvme0n1", isNvme=True)],
    )
    monkeypatch.setattr(
        collectors,
        "collect_usb_storage",
        lambda: [UsbStorageDevice(name="sdb", path="/dev/sdb", mounted=False)],
    )
    monkeypatch.setattr(
        collectors,
        "collect_tooling",
        lambda: [ToolStatus(name="clonezilla", found=True, path="/usr/bin/clonezilla")],
    )


def test_orchestrator_none_behaves_exactly_like_omitting_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`orchestrator=None` (explicit) and omitting the argument entirely
    are the same call - backward compatibility is the *default*, not a
    special case triggered only by omission.
    """
    _patch_non_discovery_collectors(monkeypatch)
    monkeypatch.setattr(collectors, "collect_cpu", lambda: CpuInfo(architecture="x86_64"))
    monkeypatch.setattr(collectors, "collect_memory", lambda: MemoryInfo(totalBytes=2048))
    monkeypatch.setattr(
        collectors,
        "collect_network",
        lambda: [NetworkInterface(name="eth0", isUp=True, isLoopback=False)],
    )

    without_argument = service.collect_host_inventory()
    with_explicit_none = service.collect_host_inventory(orchestrator=None)

    assert without_argument.cpu == with_explicit_none.cpu
    assert without_argument.memory == with_explicit_none.memory
    assert without_argument.network == with_explicit_none.network


def test_orchestrator_supplies_cpu_memory_network_instead_of_collectors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_non_discovery_collectors(monkeypatch)
    # If these were called, the test would see collector-sourced values
    # instead of snapshot-sourced ones below - proving they were *not*.
    monkeypatch.setattr(
        collectors, "collect_cpu", lambda: CpuInfo(architecture="collector-should-not-run")
    )
    monkeypatch.setattr(collectors, "collect_memory", lambda: MemoryInfo(totalBytes=-1))
    monkeypatch.setattr(collectors, "collect_network", lambda: [])

    snapshot_cpu = CpuInfo(architecture="x86_64", logicalCores=16)
    snapshot_memory = MemoryInfo(totalBytes=4096)
    snapshot_network = [NetworkInterface(name="wlan0", isUp=True, isLoopback=False)]
    orchestrator = HostDiscoveryOrchestrator(
        HostDiscoveryAdapters(
            cpu=_CountingAdapter(snapshot_cpu),
            memory=_CountingAdapter(snapshot_memory),
            network=_CountingAdapter(snapshot_network),
        )
    )

    inventory = service.collect_host_inventory(orchestrator)

    assert inventory.cpu == snapshot_cpu
    assert inventory.memory == snapshot_memory
    assert inventory.network == snapshot_network


def test_orchestrator_other_sections_unaffected(monkeypatch: pytest.MonkeyPatch) -> None:
    """identity/firmware/operating_system/efi_system_partition/storage/
    usb_storage/tooling always come from the same collectors, whether
    or not an orchestrator is given.
    """
    _patch_non_discovery_collectors(monkeypatch)
    monkeypatch.setattr(collectors, "collect_cpu", lambda: CpuInfo(architecture="x86_64"))
    monkeypatch.setattr(collectors, "collect_memory", lambda: MemoryInfo(totalBytes=1024))
    monkeypatch.setattr(collectors, "collect_network", lambda: [])

    without_orchestrator = service.collect_host_inventory()
    with_orchestrator = service.collect_host_inventory(
        HostDiscoveryOrchestrator(HostDiscoveryAdapters())
    )

    assert without_orchestrator.identity == with_orchestrator.identity
    assert without_orchestrator.firmware == with_orchestrator.firmware
    assert without_orchestrator.operating_system == with_orchestrator.operating_system
    assert without_orchestrator.efi_system_partition == with_orchestrator.efi_system_partition
    assert without_orchestrator.storage == with_orchestrator.storage
    assert without_orchestrator.usb_storage == with_orchestrator.usb_storage
    assert without_orchestrator.tooling == with_orchestrator.tooling


def test_orchestrator_is_called_exactly_once(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_non_discovery_collectors(monkeypatch)
    monkeypatch.setattr(collectors, "collect_cpu", lambda: CpuInfo(architecture="x86_64"))
    monkeypatch.setattr(collectors, "collect_memory", lambda: MemoryInfo(totalBytes=1024))
    monkeypatch.setattr(collectors, "collect_network", lambda: [])

    cpu_adapter = _CountingAdapter(CpuInfo(architecture="x86_64"))
    memory_adapter = _CountingAdapter(MemoryInfo(totalBytes=1024))
    network_adapter = _CountingAdapter([NetworkInterface(name="eth0", isUp=True, isLoopback=False)])
    orchestrator = HostDiscoveryOrchestrator(
        HostDiscoveryAdapters(cpu=cpu_adapter, memory=memory_adapter, network=network_adapter)
    )

    service.collect_host_inventory(orchestrator)

    assert cpu_adapter.call_count == 1
    assert memory_adapter.call_count == 1
    assert network_adapter.call_count == 1


def test_orchestrator_cpu_none_falls_back_to_collector(monkeypatch: pytest.MonkeyPatch) -> None:
    """The cpu slot was never wired -> the snapshot's cpu is None ->
    HostInventory.cpu (a required field) must still be populated, from
    the same collect_cpu() call that would have run without an
    orchestrator at all.
    """
    _patch_non_discovery_collectors(monkeypatch)
    fallback_cpu = CpuInfo(architecture="fallback-x86_64")
    monkeypatch.setattr(collectors, "collect_cpu", lambda: fallback_cpu)
    monkeypatch.setattr(collectors, "collect_memory", lambda: MemoryInfo(totalBytes=1024))
    monkeypatch.setattr(collectors, "collect_network", lambda: [])

    orchestrator = HostDiscoveryOrchestrator(HostDiscoveryAdapters())  # cpu slot unset
    inventory = service.collect_host_inventory(orchestrator)

    assert inventory.cpu == fallback_cpu


def test_orchestrator_memory_none_falls_back_to_collector(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_non_discovery_collectors(monkeypatch)
    fallback_memory = MemoryInfo(totalBytes=999)
    monkeypatch.setattr(collectors, "collect_cpu", lambda: CpuInfo(architecture="x86_64"))
    monkeypatch.setattr(collectors, "collect_memory", lambda: fallback_memory)
    monkeypatch.setattr(collectors, "collect_network", lambda: [])

    orchestrator = HostDiscoveryOrchestrator(HostDiscoveryAdapters())  # memory slot unset
    inventory = service.collect_host_inventory(orchestrator)

    assert inventory.memory == fallback_memory


def test_orchestrator_cpu_platform_error_falls_back_to_collector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The cpu adapter is wired but fails with a PlatformError - isolated
    *inside* the orchestrator into a caveat (snapshot.cpu is None), and
    this module falls back exactly as it does for an unwired slot.
    """
    _patch_non_discovery_collectors(monkeypatch)
    fallback_cpu = CpuInfo(architecture="fallback-after-error")
    monkeypatch.setattr(collectors, "collect_cpu", lambda: fallback_cpu)
    monkeypatch.setattr(collectors, "collect_memory", lambda: MemoryInfo(totalBytes=1024))
    monkeypatch.setattr(collectors, "collect_network", lambda: [])

    failing_cpu_adapter = _CountingAdapter(
        CpuInfo(architecture="never-returned"), error=PlatformError("cpu probe failed")
    )
    orchestrator = HostDiscoveryOrchestrator(HostDiscoveryAdapters(cpu=failing_cpu_adapter))

    inventory = service.collect_host_inventory(orchestrator)

    assert inventory.cpu == fallback_cpu
    assert failing_cpu_adapter.call_count == 1


def test_orchestrator_network_unset_stays_empty_without_calling_collector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unlike cpu/memory, network has no fallback: HostInventory.network
    already accepts an empty list validly, so an unwired network slot
    simply yields an empty list - collect_network() is never called.
    """
    _patch_non_discovery_collectors(monkeypatch)
    monkeypatch.setattr(collectors, "collect_cpu", lambda: CpuInfo(architecture="x86_64"))
    monkeypatch.setattr(collectors, "collect_memory", lambda: MemoryInfo(totalBytes=1024))
    network_calls: list[None] = []

    def _collect_network_spy() -> list[NetworkInterface]:
        network_calls.append(None)
        return [NetworkInterface(name="should-not-appear", isUp=True, isLoopback=False)]

    monkeypatch.setattr(collectors, "collect_network", _collect_network_spy)

    orchestrator = HostDiscoveryOrchestrator(HostDiscoveryAdapters())  # network slot unset
    inventory = service.collect_host_inventory(orchestrator)

    assert inventory.network == []
    assert network_calls == []


def test_orchestrator_unexpected_exception_propagates_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_non_discovery_collectors(monkeypatch)
    monkeypatch.setattr(collectors, "collect_cpu", lambda: CpuInfo(architecture="x86_64"))
    monkeypatch.setattr(collectors, "collect_memory", lambda: MemoryInfo(totalBytes=1024))
    monkeypatch.setattr(collectors, "collect_network", lambda: [])

    original = TypeError("miswired adapter")
    orchestrator = HostDiscoveryOrchestrator(
        HostDiscoveryAdapters(cpu=_CountingAdapter(CpuInfo(architecture="x86_64"), error=original))
    )

    with pytest.raises(TypeError) as exc_info:
        service.collect_host_inventory(orchestrator)
    assert exc_info.value is original
