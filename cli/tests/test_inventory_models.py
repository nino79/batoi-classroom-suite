from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from bcs.inventory.models import (
    INVENTORY_SCHEMA_VERSION,
    CpuInfo,
    FirmwareInfo,
    HostIdentity,
    HostInventory,
    MemoryInfo,
    OperatingSystemInfo,
    SecureBootState,
)


def _minimal_inventory() -> HostInventory:
    return HostInventory(
        collectedAt=datetime.now(UTC),
        identity=HostIdentity(),
        firmware=FirmwareInfo(uefi=True, secureBoot=SecureBootState.ENABLED),
        operatingSystem=OperatingSystemInfo(name="LliureX", architecture="x86_64"),
        cpu=CpuInfo(architecture="x86_64"),
        memory=MemoryInfo(),
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
