from __future__ import annotations

import pytest
from pydantic import ValidationError

from bcs.platform.adapters.network.models import NetworkInterface, NetworkInterfaceStatus


def _make_interface(**overrides: object) -> NetworkInterface:
    defaults: dict[str, object] = {
        "name": "eth0",
        "mac_address": "52:54:00:12:34:56",
        "ip_addresses": ("10.0.2.15", "fe80::5054:ff:fe12:3456"),
        "is_up": True,
        "is_loopback": False,
    }
    defaults.update(overrides)
    return NetworkInterface(**defaults)  # type: ignore[arg-type]


def _make_status(**overrides: object) -> NetworkInterfaceStatus:
    defaults: dict[str, object] = {
        "interfaces": (_make_interface(),),
        "raw_text": '[{"ifname": "eth0", ...}]',
    }
    defaults.update(overrides)
    return NetworkInterfaceStatus(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# NetworkInterface: independence from bcs.inventory.models
# ---------------------------------------------------------------------------


def test_network_interface_is_independently_defined_from_inventory_model() -> None:
    """Deliberately a separate type from bcs.inventory.models.NetworkInterface -
    see docs/NETWORK_ADAPTER.md#naming-rationale. Compatible fields (same
    concept, same field names), but never imported across the
    bcs.platform -> bcs.inventory layering boundary.
    """
    from bcs.inventory.models import NetworkInterface as InventoryNetworkInterface

    assert NetworkInterface is not InventoryNetworkInterface

    platform_fields = set(NetworkInterface.model_fields)
    inventory_fields = set(InventoryNetworkInterface.model_fields)
    assert platform_fields == inventory_fields


# ---------------------------------------------------------------------------
# NetworkInterface: construction / defaults
# ---------------------------------------------------------------------------


def test_interface_construction_with_all_fields() -> None:
    interface = _make_interface()
    assert interface.name == "eth0"
    assert interface.mac_address == "52:54:00:12:34:56"
    assert interface.ip_addresses == ("10.0.2.15", "fe80::5054:ff:fe12:3456")
    assert interface.is_up is True
    assert interface.is_loopback is False


def test_interface_mac_address_defaults_to_none() -> None:
    interface = NetworkInterface(name="lo", is_up=True, is_loopback=True)
    assert interface.mac_address is None


def test_interface_ip_addresses_defaults_to_empty_tuple() -> None:
    interface = NetworkInterface(name="eth0", is_up=False, is_loopback=False)
    assert interface.ip_addresses == ()
    assert isinstance(interface.ip_addresses, tuple)


def test_interface_populate_by_name_accepts_camel_case_aliases() -> None:
    interface = NetworkInterface(
        name="eth0",
        macAddress="52:54:00:12:34:56",
        ipAddresses=("10.0.2.15",),
        isUp=True,
        isLoopback=False,
    )
    assert interface.mac_address == "52:54:00:12:34:56"
    assert interface.ip_addresses == ("10.0.2.15",)
    assert interface.is_up is True
    assert interface.is_loopback is False


# ---------------------------------------------------------------------------
# NetworkInterface: validation
# ---------------------------------------------------------------------------


def test_interface_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        NetworkInterface.model_validate(
            {
                "name": "eth0",
                "isUp": True,
                "isLoopback": False,
                "bogus": 1,
            }
        )


@pytest.mark.parametrize("field", ["name", "isUp", "isLoopback"])
def test_interface_requires_mandatory_fields(field: str) -> None:
    data: dict[str, object] = {
        "name": "eth0",
        "isUp": True,
        "isLoopback": False,
    }
    del data[field]
    with pytest.raises(ValidationError):
        NetworkInterface.model_validate(data)


# ---------------------------------------------------------------------------
# NetworkInterface: immutability / equality / hashing
# ---------------------------------------------------------------------------


def test_interface_is_frozen() -> None:
    interface = _make_interface()
    with pytest.raises(ValidationError):
        interface.is_up = False  # type: ignore[misc]


def test_interface_equality() -> None:
    assert _make_interface() == _make_interface()
    assert _make_interface(name="eth0") != _make_interface(name="eth1")


def test_interface_is_hashable() -> None:
    assert isinstance(hash(_make_interface()), int)


# ---------------------------------------------------------------------------
# NetworkInterface: serialization / deserialization
# ---------------------------------------------------------------------------


def test_interface_json_round_trip_uses_camel_case_aliases() -> None:
    interface = _make_interface()
    data = interface.model_dump(mode="json", by_alias=True)

    assert data["macAddress"] == interface.mac_address
    assert data["ipAddresses"] == list(interface.ip_addresses)
    assert data["isUp"] == interface.is_up
    assert data["isLoopback"] == interface.is_loopback
    assert "mac_address" not in data
    assert "is_up" not in data

    reloaded = NetworkInterface.model_validate(data)
    assert reloaded == interface


def test_interface_json_round_trip_with_none_mac_address() -> None:
    interface = _make_interface(mac_address=None)
    data = interface.model_dump(mode="json", by_alias=True)
    assert data["macAddress"] is None

    reloaded = NetworkInterface.model_validate(data)
    assert reloaded == interface


# ---------------------------------------------------------------------------
# NetworkInterfaceStatus: construction / defaults
# ---------------------------------------------------------------------------


def test_status_construction_with_interfaces() -> None:
    status = _make_status()
    assert len(status.interfaces) == 1
    assert status.interfaces[0].name == "eth0"
    assert status.raw_text.startswith("[")


def test_status_interfaces_defaults_to_empty_tuple() -> None:
    status = NetworkInterfaceStatus(raw_text="[]")
    assert status.interfaces == ()
    assert isinstance(status.interfaces, tuple)


def test_status_populate_by_name_accepts_camel_case_aliases() -> None:
    status = NetworkInterfaceStatus(
        interfaces=(_make_interface(),),
        rawText="[...]",
    )
    assert status.raw_text == "[...]"


# ---------------------------------------------------------------------------
# NetworkInterfaceStatus: validation
# ---------------------------------------------------------------------------


def test_status_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        NetworkInterfaceStatus.model_validate({"rawText": "[]", "bogus": 1})


def test_status_requires_raw_text() -> None:
    with pytest.raises(ValidationError):
        NetworkInterfaceStatus.model_validate({})


# ---------------------------------------------------------------------------
# NetworkInterfaceStatus: immutability / equality / hashing
# ---------------------------------------------------------------------------


def test_status_is_frozen() -> None:
    status = _make_status()
    with pytest.raises(ValidationError):
        status.raw_text = "changed"  # type: ignore[misc]


def test_status_nested_interfaces_are_frozen() -> None:
    status = _make_status()
    with pytest.raises(ValidationError):
        status.interfaces[0].is_up = False  # type: ignore[misc]


def test_status_equality() -> None:
    assert _make_status() == _make_status()
    assert _make_status(raw_text="[]") != _make_status()


def test_status_is_hashable() -> None:
    """Every field here is a str or a tuple of frozen models with only
    str/bool/tuple[str, ...] fields - no plain list - so
    NetworkInterfaceStatus is unconditionally hashable, matching
    FilesystemUsageReport's identical reasoning.
    """
    assert isinstance(hash(_make_status()), int)
    assert isinstance(hash(NetworkInterfaceStatus(raw_text="[]")), int)


# ---------------------------------------------------------------------------
# NetworkInterfaceStatus: serialization / deserialization
# ---------------------------------------------------------------------------


def test_status_json_round_trip_uses_camel_case_aliases() -> None:
    status = _make_status()
    data = status.model_dump(mode="json", by_alias=True)

    assert "interfaces" in data
    assert data["rawText"] == status.raw_text
    assert "raw_text" not in data
    assert data["interfaces"][0]["isUp"] is True

    reloaded = NetworkInterfaceStatus.model_validate(data)
    assert reloaded == status


def test_status_json_round_trip_with_defaults() -> None:
    status = NetworkInterfaceStatus(raw_text="[]")
    data = status.model_dump(mode="json", by_alias=True)

    assert data["interfaces"] == []

    reloaded = NetworkInterfaceStatus.model_validate(data)
    assert reloaded == status


def test_status_json_round_trip_with_multiple_interfaces() -> None:
    eth0 = _make_interface(name="eth0")
    lo = _make_interface(name="lo", mac_address=None, ip_addresses=("127.0.0.1",), is_loopback=True)
    status = NetworkInterfaceStatus(interfaces=(eth0, lo), raw_text="[...]")

    data = status.model_dump(mode="json", by_alias=True)
    reloaded = NetworkInterfaceStatus.model_validate(data)

    assert len(reloaded.interfaces) == 2
    assert reloaded == status
