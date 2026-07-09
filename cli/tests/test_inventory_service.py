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
from bcs.platform.adapters.network.models import (
    NetworkInterface as PlatformNetworkInterface,
)
from bcs.platform.adapters.network.models import NetworkInterfaceStatus
from bcs.platform.adapters.storage.models import BlockDevice, Partition, StorageConfiguration
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


def _make_block_device(
    *, name: str = "sda", is_nvme: bool = False, device_type: str = "disk", **overrides: object
) -> BlockDevice:
    """Build a minimal, valid ``BlockDevice`` for storage-translation
    tests (issue #70) - only the fields that matter for a given test
    need overriding.
    """
    defaults: dict[str, object] = {
        "name": name,
        "path": f"/dev/{name}",
        "deviceType": device_type,
        "isRemovable": False,
        "isReadOnly": False,
        "isNvme": is_nvme,
    }
    defaults.update(overrides)
    return BlockDevice(**defaults)  # type: ignore[arg-type]


def _make_platform_network_interface(**overrides: object) -> PlatformNetworkInterface:
    """Build a minimal, valid Platform Layer ``NetworkInterface`` for
    network-translation tests (Beta M3, Network Adapter wiring) - only
    the fields that matter for a given test need overriding.
    """
    defaults: dict[str, object] = {
        "name": "eth0",
        "macAddress": "52:54:00:12:34:56",
        "ipAddresses": ("192.0.2.10",),
        "isUp": True,
        "isLoopback": False,
    }
    defaults.update(overrides)
    return PlatformNetworkInterface(**defaults)  # type: ignore[arg-type]


def _make_network_interface_status(
    *, interfaces: tuple[PlatformNetworkInterface, ...] | None = None
) -> NetworkInterfaceStatus:
    return NetworkInterfaceStatus(
        interfaces=interfaces if interfaces is not None else (_make_platform_network_interface(),),
        rawText="eth0\n",
    )


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
    """Patch every collector *other than* cpu/memory/network/storage -
    the six sections that must be unaffected by whether an orchestrator
    is given, per this module's own docstring. ``collect_storage`` is
    also patched here as a convenient, fixed fallback value for tests
    that don't care about storage specifically (most cpu/memory/network
    -focused tests) - it is *not* asserting storage is unaffected (see
    issue #70's own dedicated storage tests for that boundary instead).
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


def test_orchestrator_supplies_cpu_memory_instead_of_collectors(
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
    orchestrator = HostDiscoveryOrchestrator(
        HostDiscoveryAdapters(
            cpu=_CountingAdapter(snapshot_cpu),
            memory=_CountingAdapter(snapshot_memory),
        )
    )

    inventory = service.collect_host_inventory(orchestrator)

    assert inventory.cpu == snapshot_cpu
    assert inventory.memory == snapshot_memory


def test_orchestrator_supplies_network_instead_of_collector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mirrors ``test_orchestrator_supplies_storage_instead_of_collector``,
    for ``network`` (Beta M3, Network Adapter wiring) - the "adapter
    path" case.
    """
    _patch_non_discovery_collectors(monkeypatch)
    monkeypatch.setattr(collectors, "collect_cpu", lambda: CpuInfo(architecture="x86_64"))
    monkeypatch.setattr(collectors, "collect_memory", lambda: MemoryInfo(totalBytes=1024))
    # If this were called, the test would see the collector-sourced
    # interface below, instead of the adapter-sourced one - proving it
    # was *not*.
    monkeypatch.setattr(
        collectors,
        "collect_network",
        lambda: [NetworkInterface(name="collector-should-not-run", isUp=True, isLoopback=False)],
    )

    snapshot_network = _make_network_interface_status()
    orchestrator = HostDiscoveryOrchestrator(
        HostDiscoveryAdapters(network=_CountingAdapter(snapshot_network))
    )

    inventory = service.collect_host_inventory(orchestrator)

    assert len(inventory.network) == 1
    assert inventory.network[0].name == "eth0"
    assert inventory.network[0].mac_address == "52:54:00:12:34:56"
    assert inventory.network[0].ip_addresses == ["192.0.2.10"]
    assert inventory.network[0].is_up is True
    assert inventory.network[0].is_loopback is False


def test_orchestrator_other_sections_unaffected(monkeypatch: pytest.MonkeyPatch) -> None:
    """identity/firmware/operating_system/efi_system_partition/
    usb_storage/tooling always come from the same collectors, whether
    or not an orchestrator is given. ``storage`` and ``network`` are
    deliberately not asserted here since issue #70 / Beta M3 - both now
    have their own fallback-with-translation behaviour, covered by the
    dedicated storage/network tests below.
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
    assert without_orchestrator.usb_storage == with_orchestrator.usb_storage
    assert without_orchestrator.tooling == with_orchestrator.tooling


def test_orchestrator_is_called_exactly_once(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_non_discovery_collectors(monkeypatch)
    monkeypatch.setattr(collectors, "collect_cpu", lambda: CpuInfo(architecture="x86_64"))
    monkeypatch.setattr(collectors, "collect_memory", lambda: MemoryInfo(totalBytes=1024))
    monkeypatch.setattr(collectors, "collect_network", lambda: [])

    cpu_adapter = _CountingAdapter(CpuInfo(architecture="x86_64"))
    memory_adapter = _CountingAdapter(MemoryInfo(totalBytes=1024))
    network_adapter = _CountingAdapter(_make_network_interface_status())
    storage_adapter = _CountingAdapter(StorageConfiguration())
    orchestrator = HostDiscoveryOrchestrator(
        HostDiscoveryAdapters(
            cpu=cpu_adapter,
            memory=memory_adapter,
            network=network_adapter,
            storage=storage_adapter,
        )
    )

    service.collect_host_inventory(orchestrator)

    assert cpu_adapter.call_count == 1
    assert memory_adapter.call_count == 1
    assert network_adapter.call_count == 1
    assert storage_adapter.call_count == 1


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


def test_orchestrator_supplies_storage_instead_of_collector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mirrors ``test_orchestrator_supplies_cpu_memory_instead_of_collectors``,
    for ``storage`` (issue #70).
    """
    _patch_non_discovery_collectors(monkeypatch)
    monkeypatch.setattr(collectors, "collect_cpu", lambda: CpuInfo(architecture="x86_64"))
    monkeypatch.setattr(collectors, "collect_memory", lambda: MemoryInfo(totalBytes=1024))
    monkeypatch.setattr(collectors, "collect_network", lambda: [])
    # If this were called, the test would see the collector-sourced NVMe
    # device _patch_non_discovery_collectors wires up, instead of the
    # SATA device supplied via the snapshot below - proving it was *not*.
    monkeypatch.setattr(
        collectors,
        "collect_storage",
        lambda: [StorageDevice(name="collector-should-not-run", path="/dev/nvme9n9", isNvme=True)],
    )

    snapshot_storage = StorageConfiguration(devices=(_make_block_device(name="sda"),))
    orchestrator = HostDiscoveryOrchestrator(
        HostDiscoveryAdapters(storage=_CountingAdapter(snapshot_storage))
    )

    inventory = service.collect_host_inventory(orchestrator)

    assert len(inventory.storage) == 1
    assert inventory.storage[0].name == "sda"
    assert inventory.storage[0].path == "/dev/sda"
    assert inventory.storage[0].is_nvme is False


def test_orchestrator_storage_unset_falls_back_to_collector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The storage slot was never wired -> snapshot.storage_topology is
    None -> falls back to the same collect_storage() call that would
    have run without an orchestrator at all - the identical shape
    already established for cpu/memory (issue #70).
    """
    _patch_non_discovery_collectors(monkeypatch)
    monkeypatch.setattr(collectors, "collect_cpu", lambda: CpuInfo(architecture="x86_64"))
    monkeypatch.setattr(collectors, "collect_memory", lambda: MemoryInfo(totalBytes=1024))
    monkeypatch.setattr(collectors, "collect_network", lambda: [])
    fallback_storage = [StorageDevice(name="nvme0n1", path="/dev/nvme0n1", isNvme=True)]
    monkeypatch.setattr(collectors, "collect_storage", lambda: fallback_storage)

    orchestrator = HostDiscoveryOrchestrator(HostDiscoveryAdapters())  # storage slot unset
    inventory = service.collect_host_inventory(orchestrator)

    assert inventory.storage == fallback_storage


def test_orchestrator_storage_platform_error_falls_back_to_collector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The storage adapter is wired but fails with a PlatformError -
    isolated *inside* the orchestrator into a caveat
    (snapshot.storage_topology is None), and this module falls back
    exactly as it does for an unwired slot (issue #70).
    """
    _patch_non_discovery_collectors(monkeypatch)
    monkeypatch.setattr(collectors, "collect_cpu", lambda: CpuInfo(architecture="x86_64"))
    monkeypatch.setattr(collectors, "collect_memory", lambda: MemoryInfo(totalBytes=1024))
    monkeypatch.setattr(collectors, "collect_network", lambda: [])
    fallback_storage = [StorageDevice(name="nvme0n1", path="/dev/nvme0n1", isNvme=True)]
    monkeypatch.setattr(collectors, "collect_storage", lambda: fallback_storage)

    failing_storage_adapter = _CountingAdapter(
        StorageConfiguration(), error=PlatformError("lsblk not found")
    )
    orchestrator = HostDiscoveryOrchestrator(HostDiscoveryAdapters(storage=failing_storage_adapter))

    inventory = service.collect_host_inventory(orchestrator)

    assert inventory.storage == fallback_storage
    assert failing_storage_adapter.call_count == 1


def test_orchestrator_network_unset_falls_back_to_collector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The network slot was never wired -> snapshot.network is None ->
    falls back to the same collect_network() call that would have run
    without an orchestrator at all - the identical shape already
    established for cpu/memory/storage (Beta M3, "fallback path").
    """
    _patch_non_discovery_collectors(monkeypatch)
    monkeypatch.setattr(collectors, "collect_cpu", lambda: CpuInfo(architecture="x86_64"))
    monkeypatch.setattr(collectors, "collect_memory", lambda: MemoryInfo(totalBytes=1024))
    fallback_network = [NetworkInterface(name="eth0", isUp=True, isLoopback=False)]
    monkeypatch.setattr(collectors, "collect_network", lambda: fallback_network)

    orchestrator = HostDiscoveryOrchestrator(HostDiscoveryAdapters())  # network slot unset
    inventory = service.collect_host_inventory(orchestrator)

    assert inventory.network == fallback_network


def test_orchestrator_network_platform_error_falls_back_to_collector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The network adapter is wired but fails with a PlatformError -
    isolated *inside* the orchestrator into a caveat (snapshot.network
    is None), and this module falls back exactly as it does for an
    unwired slot (Beta M3, "isolated PlatformError").
    """
    _patch_non_discovery_collectors(monkeypatch)
    monkeypatch.setattr(collectors, "collect_cpu", lambda: CpuInfo(architecture="x86_64"))
    monkeypatch.setattr(collectors, "collect_memory", lambda: MemoryInfo(totalBytes=1024))
    fallback_network = [NetworkInterface(name="eth0", isUp=True, isLoopback=False)]
    monkeypatch.setattr(collectors, "collect_network", lambda: fallback_network)

    failing_network_adapter = _CountingAdapter(
        _make_network_interface_status(), error=PlatformError("ip not found")
    )
    orchestrator = HostDiscoveryOrchestrator(HostDiscoveryAdapters(network=failing_network_adapter))

    inventory = service.collect_host_inventory(orchestrator)

    assert inventory.network == fallback_network
    assert failing_network_adapter.call_count == 1


def test_collect_host_inventory_without_orchestrator_uses_collect_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No orchestrator given at all (Beta M3, "orchestrator unavailable")
    - behaviour is byte-for-byte identical to before the Network Adapter
    was wired in: ``network`` comes straight from ``collect_network()``.
    """
    _patch_non_discovery_collectors(monkeypatch)
    monkeypatch.setattr(collectors, "collect_cpu", lambda: CpuInfo(architecture="x86_64"))
    monkeypatch.setattr(collectors, "collect_memory", lambda: MemoryInfo(totalBytes=1024))
    expected_network = [NetworkInterface(name="eth0", isUp=True, isLoopback=False)]
    monkeypatch.setattr(collectors, "collect_network", lambda: expected_network)

    inventory = service.collect_host_inventory()

    assert inventory.network == expected_network


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


# ---------------------------------------------------------------------------
# Storage translation (service._translate_storage_devices, issue #70)
# ---------------------------------------------------------------------------


def test_translate_storage_devices_empty_configuration() -> None:
    assert service._translate_storage_devices(StorageConfiguration()) == []


def test_translate_storage_devices_single_nvme_device() -> None:
    config = StorageConfiguration(
        devices=(_make_block_device(name="nvme0n1", is_nvme=True, sizeBytes=512110190592),)
    )

    result = service._translate_storage_devices(config)

    assert len(result) == 1
    assert result[0] == StorageDevice(
        name="nvme0n1", path="/dev/nvme0n1", isNvme=True, sizeBytes=512110190592
    )


def test_translate_storage_devices_single_sata_device() -> None:
    config = StorageConfiguration(
        devices=(_make_block_device(name="sda", is_nvme=False, sizeBytes=500107862016),)
    )

    result = service._translate_storage_devices(config)

    assert len(result) == 1
    assert result[0] == StorageDevice(
        name="sda", path="/dev/sda", isNvme=False, sizeBytes=500107862016
    )


def test_translate_storage_devices_multiple_devices_preserve_order() -> None:
    config = StorageConfiguration(
        devices=(
            _make_block_device(name="sda", is_nvme=False),
            _make_block_device(name="nvme0n1", is_nvme=True),
            _make_block_device(name="sdb", is_nvme=False),
        )
    )

    result = service._translate_storage_devices(config)

    assert [device.name for device in result] == ["sda", "nvme0n1", "sdb"]


def test_translate_storage_devices_none_size_and_model_pass_through() -> None:
    config = StorageConfiguration(
        devices=(_make_block_device(name="sda", sizeBytes=None, model=None),)
    )

    result = service._translate_storage_devices(config)

    assert result[0].size_bytes is None
    assert result[0].model is None


def test_translate_storage_devices_model_is_preserved() -> None:
    config = StorageConfiguration(devices=(_make_block_device(name="sda", model="Samsung 860"),))

    result = service._translate_storage_devices(config)

    assert result[0].model == "Samsung 860"


def test_translate_storage_devices_filters_out_non_disk_device_types() -> None:
    """A loop device (e.g. a mounted ISO) or a CD-ROM drive must not
    appear in ``bcs inventory``'s storage list - the legacy collector's
    NVMe-only glob could never match one, so this translation must not
    silently start reporting devices ``bcs inventory storage`` never
    included before (issue #70).
    """
    config = StorageConfiguration(
        devices=(
            _make_block_device(name="loop0", device_type="loop"),
            _make_block_device(name="sr0", device_type="rom"),
        )
    )

    assert service._translate_storage_devices(config) == []


def test_translate_storage_devices_mixed_disk_and_non_disk_keeps_only_disks() -> None:
    config = StorageConfiguration(
        devices=(
            _make_block_device(name="sda", device_type="disk"),
            _make_block_device(name="loop0", device_type="loop"),
        )
    )

    result = service._translate_storage_devices(config)

    assert [device.name for device in result] == ["sda"]


def test_translate_storage_devices_does_not_carry_over_partitions_or_mounts() -> None:
    """``StorageDevice`` has no field for either - this is a deliberate
    narrowing translation, not a passthrough (issue #70)."""
    device_with_partition = _make_block_device(
        name="sda",
        partitions=(Partition(name="sda1", path="/dev/sda1", number=1),),
        mountPoint="/",
    )
    config = StorageConfiguration(devices=(device_with_partition,))

    result = service._translate_storage_devices(config)

    assert result == [StorageDevice(name="sda", path="/dev/sda", isNvme=False)]


# ---------------------------------------------------------------------------
# Network translation (service._translate_network_interfaces, Beta M3)
# ---------------------------------------------------------------------------


def test_translate_network_interfaces_empty_status() -> None:
    assert service._translate_network_interfaces(NetworkInterfaceStatus(rawText="")) == []


def test_translate_network_interfaces_single_ipv4_interface() -> None:
    status = _make_network_interface_status(
        interfaces=(_make_platform_network_interface(name="eth0", ipAddresses=("192.0.2.10",)),)
    )

    result = service._translate_network_interfaces(status)

    assert len(result) == 1
    assert result[0] == NetworkInterface(
        name="eth0",
        macAddress="52:54:00:12:34:56",
        ipAddresses=["192.0.2.10"],
        isUp=True,
        isLoopback=False,
    )


def test_translate_network_interfaces_single_ipv6_interface() -> None:
    status = _make_network_interface_status(
        interfaces=(_make_platform_network_interface(name="eth0", ipAddresses=("2001:db8::1",)),)
    )

    result = service._translate_network_interfaces(status)

    assert result[0].ip_addresses == ["2001:db8::1"]


def test_translate_network_interfaces_multiple_addresses() -> None:
    status = _make_network_interface_status(
        interfaces=(
            _make_platform_network_interface(
                name="eth0", ipAddresses=("192.0.2.10", "2001:db8::1", "192.0.2.11")
            ),
        )
    )

    result = service._translate_network_interfaces(status)

    assert result[0].ip_addresses == ["192.0.2.10", "2001:db8::1", "192.0.2.11"]


def test_translate_network_interfaces_interface_without_addresses() -> None:
    status = _make_network_interface_status(
        interfaces=(_make_platform_network_interface(name="eth1", ipAddresses=()),)
    )

    result = service._translate_network_interfaces(status)

    assert result[0].ip_addresses == []


def test_translate_network_interfaces_loopback_interface() -> None:
    status = _make_network_interface_status(
        interfaces=(
            _make_platform_network_interface(
                name="lo",
                macAddress=None,
                ipAddresses=("127.0.0.1",),
                isUp=True,
                isLoopback=True,
            ),
        )
    )

    result = service._translate_network_interfaces(status)

    assert result[0].name == "lo"
    assert result[0].mac_address is None
    assert result[0].is_loopback is True


def test_translate_network_interfaces_multiple_interfaces_preserve_order() -> None:
    status = _make_network_interface_status(
        interfaces=(
            _make_platform_network_interface(name="lo", isLoopback=True),
            _make_platform_network_interface(name="eth0"),
            _make_platform_network_interface(name="wlan0"),
        )
    )

    result = service._translate_network_interfaces(status)

    assert [iface.name for iface in result] == ["lo", "eth0", "wlan0"]


def test_translate_network_interfaces_does_not_carry_over_raw_text() -> None:
    """``NetworkInterface`` (``HostInventory``) has no field for
    ``NetworkInterfaceStatus.raw_text`` - this is a deliberate narrowing
    translation, not a passthrough (Beta M3, mirroring issue #70's own
    ``StorageDevice`` translation).
    """
    status = _make_network_interface_status()

    result = service._translate_network_interfaces(status)

    assert result == [
        NetworkInterface(
            name="eth0",
            macAddress="52:54:00:12:34:56",
            ipAddresses=["192.0.2.10"],
            isUp=True,
            isLoopback=False,
        )
    ]
