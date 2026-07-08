from __future__ import annotations

import dataclasses

import pytest
from pydantic import ValidationError

from bcs.inventory.discovery.models import HostDiscoveryAdapters, HostDiscoverySnapshot
from bcs.inventory.models import CpuInfo, MemoryInfo, NetworkInterface
from bcs.platform.adapters.efi.models import FirmwareBootConfiguration
from bcs.platform.adapters.secureboot.models import SecureBootState, SecureBootStatus
from bcs.platform.adapters.storage.models import StorageConfiguration


def _make_firmware_boot_configuration() -> FirmwareBootConfiguration:
    return FirmwareBootConfiguration(raw_text="BootCurrent: 0000\n")


def _make_storage_configuration() -> StorageConfiguration:
    return StorageConfiguration()


def _make_secure_boot_status() -> SecureBootStatus:
    return SecureBootStatus(state=SecureBootState.ENABLED, raw_text="SecureBoot enabled\n")


def _make_cpu_info() -> CpuInfo:
    return CpuInfo(architecture="x86_64", model="Intel(R) Core(TM) i5", logical_cores=8)


def _make_memory_info() -> MemoryInfo:
    return MemoryInfo(total_bytes=17179869184, available_bytes=9663676416)


def _make_network_interface(**overrides: object) -> NetworkInterface:
    defaults: dict[str, object] = {
        "name": "eth0",
        "mac_address": "aa:bb:cc:dd:ee:ff",
        "ip_addresses": [],
        "is_up": True,
        "is_loopback": False,
    }
    defaults.update(overrides)
    return NetworkInterface(**defaults)  # type: ignore[arg-type]


def _make_snapshot(**overrides: object) -> HostDiscoverySnapshot:
    defaults: dict[str, object] = {
        "firmware_boot_configuration": _make_firmware_boot_configuration(),
        "storage_topology": _make_storage_configuration(),
        "secure_boot": None,
        "filesystem": None,
        "network": (_make_network_interface(),),
        "cpu": _make_cpu_info(),
        "memory": _make_memory_info(),
        "tpm": None,
        "caveats": (),
    }
    defaults.update(overrides)
    return HostDiscoverySnapshot(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# HostDiscoveryAdapters
# ---------------------------------------------------------------------------


def test_adapters_defaults_are_all_none() -> None:
    adapters = HostDiscoveryAdapters()

    assert adapters.efi is None
    assert adapters.storage is None
    assert adapters.secure_boot is None
    assert adapters.filesystem is None
    assert adapters.network is None
    assert adapters.cpu is None
    assert adapters.memory is None
    assert adapters.tpm is None


def test_adapters_construction_with_all_slots_bound() -> None:
    efi_callable = _make_firmware_boot_configuration
    storage_callable = _make_storage_configuration
    secure_boot_callable = _make_secure_boot_status
    cpu_callable = _make_cpu_info
    memory_callable = _make_memory_info
    network_callable = lambda: [_make_network_interface()]  # noqa: E731

    adapters = HostDiscoveryAdapters(
        efi=efi_callable,
        storage=storage_callable,
        secure_boot=secure_boot_callable,
        filesystem=lambda: object(),
        network=network_callable,
        cpu=cpu_callable,
        memory=memory_callable,
        tpm=lambda: object(),
    )

    assert adapters.efi is efi_callable
    assert adapters.efi() == _make_firmware_boot_configuration()
    assert adapters.storage is storage_callable
    assert adapters.cpu is cpu_callable
    assert adapters.memory is memory_callable
    assert adapters.network is network_callable
    assert adapters.network() == [_make_network_interface()]
    assert adapters.secure_boot is secure_boot_callable
    assert adapters.secure_boot() == _make_secure_boot_status()
    assert callable(adapters.filesystem)
    assert callable(adapters.tpm)


def test_adapters_is_a_frozen_dataclass() -> None:
    assert dataclasses.is_dataclass(HostDiscoveryAdapters)
    adapters = HostDiscoveryAdapters()
    with pytest.raises(dataclasses.FrozenInstanceError):
        adapters.efi = _make_firmware_boot_configuration  # type: ignore[misc]


def test_adapters_equality() -> None:
    assert HostDiscoveryAdapters() == HostDiscoveryAdapters()

    shared_callable = _make_cpu_info
    assert HostDiscoveryAdapters(cpu=shared_callable) == HostDiscoveryAdapters(cpu=shared_callable)
    assert HostDiscoveryAdapters(cpu=_make_cpu_info) != HostDiscoveryAdapters(
        cpu=_make_memory_info  # type: ignore[arg-type]
    )


def test_adapters_is_hashable() -> None:
    assert isinstance(hash(HostDiscoveryAdapters()), int)
    assert isinstance(hash(HostDiscoveryAdapters(cpu=_make_cpu_info)), int)


# ---------------------------------------------------------------------------
# HostDiscoverySnapshot: construction / defaults
# ---------------------------------------------------------------------------


def test_snapshot_defaults_are_absent_or_empty() -> None:
    snapshot = HostDiscoverySnapshot()

    assert snapshot.firmware_boot_configuration is None
    assert snapshot.storage_topology is None
    assert snapshot.secure_boot is None
    assert snapshot.filesystem is None
    assert snapshot.network == ()
    assert snapshot.cpu is None
    assert snapshot.memory is None
    assert snapshot.tpm is None
    assert snapshot.caveats == ()


def test_snapshot_construction_with_every_field_populated() -> None:
    snapshot = _make_snapshot()

    assert snapshot.firmware_boot_configuration is not None
    assert snapshot.storage_topology is not None
    assert len(snapshot.network) == 1
    assert snapshot.cpu is not None
    assert snapshot.cpu.architecture == "x86_64"
    assert snapshot.memory is not None
    assert snapshot.memory.total_bytes == 17179869184


def test_snapshot_populate_by_name_accepts_camel_case_aliases() -> None:
    snapshot = HostDiscoverySnapshot(
        firmwareBootConfiguration=_make_firmware_boot_configuration(),
        storageTopology=_make_storage_configuration(),
        secureBoot=None,
        filesystem=None,
        network=(),
        cpu=_make_cpu_info(),
        memory=_make_memory_info(),
        tpm=None,
        caveats=(),
    )
    assert snapshot.firmware_boot_configuration is not None
    assert snapshot.storage_topology is not None


def test_snapshot_accepts_opaque_filesystem_tpm_values() -> None:
    """filesystem/tpm are typed `object | None` - deliberately generic
    since no adapter design exists yet for either of them.
    """
    snapshot = _make_snapshot(filesystem={"k": "v"}, tpm=123)
    assert snapshot.filesystem == {"k": "v"}
    assert snapshot.tpm == 123


def test_snapshot_accepts_secure_boot_status() -> None:
    """secure_boot is typed `SecureBootStatus | None` - the concrete
    model, now that the Secure Boot Adapter is accepted and implemented.
    """
    status = _make_secure_boot_status()
    snapshot = _make_snapshot(secure_boot=status)
    assert snapshot.secure_boot == status


def test_snapshot_caveats_can_be_populated() -> None:
    snapshot = _make_snapshot(caveats=("efi: FirmwareBootUnavailableError: no UEFI",))
    assert snapshot.caveats == ("efi: FirmwareBootUnavailableError: no UEFI",)


# ---------------------------------------------------------------------------
# HostDiscoverySnapshot: validation
# ---------------------------------------------------------------------------


def test_snapshot_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        HostDiscoverySnapshot.model_validate({"bogus": 1})


# ---------------------------------------------------------------------------
# HostDiscoverySnapshot: immutability / equality / hashing
# ---------------------------------------------------------------------------


def test_snapshot_is_frozen() -> None:
    snapshot = HostDiscoverySnapshot()
    with pytest.raises(ValidationError):
        snapshot.cpu = _make_cpu_info()  # type: ignore[misc]


def test_snapshot_nested_models_are_frozen() -> None:
    snapshot = _make_snapshot()
    assert snapshot.cpu is not None
    with pytest.raises(ValidationError):
        snapshot.cpu.model = "changed"  # type: ignore[misc]


def test_snapshot_equality() -> None:
    assert HostDiscoverySnapshot() == HostDiscoverySnapshot()
    assert _make_snapshot() == _make_snapshot()
    assert _make_snapshot(caveats=("x",)) != _make_snapshot()


def test_snapshot_is_hashable_when_network_is_empty() -> None:
    snapshot = HostDiscoverySnapshot()
    assert isinstance(hash(snapshot), int)


def test_snapshot_hash_raises_whenever_network_is_non_empty() -> None:
    """Documented, not a bug: ``NetworkInterface`` carries its own
    ``ip_addresses: list[str]`` field, and Pydantic's generated
    ``__hash__`` fails on a ``list``-typed field regardless of whether
    that list happens to be empty - a plain ``list`` is never hashable
    by type, independent of its contents. Any ``HostDiscoverySnapshot``
    with at least one ``NetworkInterface`` in ``network`` is therefore
    unhashable, matching ``HostInventory``'s own same limitation - see
    this module's own docstring.
    """
    snapshot = _make_snapshot(network=(_make_network_interface(),))
    with pytest.raises(TypeError):
        hash(snapshot)


# ---------------------------------------------------------------------------
# HostDiscoverySnapshot: serialization / deserialization
# ---------------------------------------------------------------------------


def test_snapshot_json_round_trip_with_defaults() -> None:
    snapshot = HostDiscoverySnapshot()
    data = snapshot.model_dump(mode="json", by_alias=True)

    assert data["firmwareBootConfiguration"] is None
    assert data["storageTopology"] is None
    assert data["network"] == []
    assert data["caveats"] == []

    reloaded = HostDiscoverySnapshot.model_validate(data)
    assert reloaded == snapshot


def test_snapshot_json_round_trip_uses_camel_case_aliases() -> None:
    snapshot = _make_snapshot()
    data = snapshot.model_dump(mode="json", by_alias=True)

    assert "firmwareBootConfiguration" in data
    assert "storageTopology" in data
    assert "firmware_boot_configuration" not in data
    assert data["cpu"]["architecture"] == "x86_64"
    assert len(data["network"]) == 1

    reloaded = HostDiscoverySnapshot.model_validate(data)
    assert reloaded == snapshot
