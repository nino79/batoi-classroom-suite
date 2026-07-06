from __future__ import annotations

import pytest

from bcs.inventory import collectors, service
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
