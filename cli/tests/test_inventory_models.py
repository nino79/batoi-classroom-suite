from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from bcs.inventory.models import (
    INVENTORY_SCHEMA_VERSION,
    CpuInfo,
    EfiSystemPartition,
    FirmwareInfo,
    HostIdentity,
    HostInventory,
    MemoryInfo,
    OperatingSystemInfo,
    SecureBootState,
    UsbStorageDevice,
)


def _minimal_inventory() -> HostInventory:
    return HostInventory(
        collectedAt=datetime.now(UTC),
        identity=HostIdentity(),
        firmware=FirmwareInfo(uefi=True, secureBoot=SecureBootState.ENABLED),
        operatingSystem=OperatingSystemInfo(name="LliureX", architecture="x86_64"),
        cpu=CpuInfo(architecture="x86_64"),
        memory=MemoryInfo(),
        efiSystemPartition=EfiSystemPartition(present=False, mounted=False),
    )


def test_default_schema_version() -> None:
    inventory = _minimal_inventory()
    assert inventory.schema_version == INVENTORY_SCHEMA_VERSION


def test_json_round_trip_uses_camel_case_aliases() -> None:
    inventory = _minimal_inventory()
    data = inventory.model_dump(mode="json", by_alias=True)
    assert "schemaVersion" in data
    assert "collectedAt" in data
    assert "operatingSystem" in data
    assert data["firmware"]["secureBoot"] == "enabled"

    # Round trip: the aliased JSON shape must parse back cleanly.
    reloaded = HostInventory.model_validate(data)
    assert reloaded == inventory


def test_root_model_is_frozen() -> None:
    inventory = _minimal_inventory()
    with pytest.raises(ValidationError):
        inventory.collected_at = datetime.now(UTC)  # type: ignore[misc]


def test_nested_model_is_frozen() -> None:
    inventory = _minimal_inventory()
    with pytest.raises(ValidationError):
        inventory.firmware.uefi = False  # type: ignore[misc]


def test_scalar_only_submodels_are_hashable() -> None:
    firmware = FirmwareInfo(uefi=True, secureBoot=SecureBootState.ENABLED)
    assert isinstance(hash(firmware), int)
    identity = HostIdentity(primaryMacAddress="aa:bb:cc:dd:ee:ff")
    assert isinstance(hash(identity), int)


def test_root_model_with_list_fields_is_not_hashable() -> None:
    inventory = _minimal_inventory()
    with pytest.raises(TypeError):
        hash(inventory)


def test_root_allows_x_prefixed_extension_field() -> None:
    data = _minimal_inventory().model_dump(mode="json", by_alias=True)
    data["x-site-note"] = "extra info"
    inventory = HostInventory.model_validate(data)
    assert inventory.model_extra == {"x-site-note": "extra info"}


def test_root_rejects_unknown_non_x_field() -> None:
    data = _minimal_inventory().model_dump(mode="json", by_alias=True)
    data["notAllowed"] = "nope"
    with pytest.raises(ValidationError, match="unexpected property"):
        HostInventory.model_validate(data)


def test_firmware_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        FirmwareInfo.model_validate({"uefi": True, "secureBoot": "enabled", "bogus": 1})


def test_secure_boot_state_values() -> None:
    assert {s.value for s in SecureBootState} == {"enabled", "disabled", "unsupported", "unknown"}


# ---------------------------------------------------------------------------
# EFI System Partition / USB storage
# ---------------------------------------------------------------------------


def test_efi_system_partition_absent_default() -> None:
    esp = EfiSystemPartition(present=False, mounted=False)
    assert esp.device is None
    assert esp.partition is None
    assert esp.mount_point is None


def test_efi_system_partition_present_round_trips_camel_case() -> None:
    esp = EfiSystemPartition(
        present=True,
        device="/dev/nvme0n1",
        partition="/dev/nvme0n1p1",
        uuid="ABCD-1234",
        filesystem="vfat",
        mountPoint="/boot/efi",
        sizeBytes=536_870_912,
        freeBytes=100_000_000,
        mounted=True,
    )
    data = esp.model_dump(mode="json", by_alias=True)
    assert data["mountPoint"] == "/boot/efi"
    assert data["sizeBytes"] == 536_870_912
    assert data["freeBytes"] == 100_000_000
    assert EfiSystemPartition.model_validate(data) == esp


def test_efi_system_partition_is_frozen() -> None:
    esp = EfiSystemPartition(present=False, mounted=False)
    with pytest.raises(ValidationError):
        esp.present = True  # type: ignore[misc]


def test_efi_system_partition_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        EfiSystemPartition.model_validate({"present": False, "mounted": False, "bogus": 1})


def test_usb_storage_device_round_trips_camel_case() -> None:
    device = UsbStorageDevice(
        name="sdb",
        path="/dev/sdb",
        vendor="SanDisk",
        model="Ultra",
        sizeBytes=16_000_000_000,
        mounted=True,
        mountPoint="/media/usb0",
    )
    data = device.model_dump(mode="json", by_alias=True)
    assert data["sizeBytes"] == 16_000_000_000
    assert data["mountPoint"] == "/media/usb0"
    assert UsbStorageDevice.model_validate(data) == device


def test_usb_storage_device_not_mounted_has_no_mount_point() -> None:
    device = UsbStorageDevice(name="sdb", path="/dev/sdb", mounted=False)
    assert device.mount_point is None


def test_usb_storage_device_is_frozen() -> None:
    device = UsbStorageDevice(name="sdb", path="/dev/sdb", mounted=False)
    with pytest.raises(ValidationError):
        device.mounted = True  # type: ignore[misc]


def test_host_inventory_exposes_efi_system_partition_and_usb_storage() -> None:
    inventory = _minimal_inventory()
    assert inventory.efi_system_partition == EfiSystemPartition(present=False, mounted=False)
    assert inventory.usb_storage == []

    data = inventory.model_dump(mode="json", by_alias=True)
    assert "efiSystemPartition" in data
    assert "usbStorage" in data
