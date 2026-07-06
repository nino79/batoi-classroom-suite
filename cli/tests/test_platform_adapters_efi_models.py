from __future__ import annotations

import pytest
from pydantic import ValidationError

from bcs.platform.adapters.efi.models import BootEntry, FirmwareBootConfiguration

_DEVICE_PATH = r"HD(1,GPT,1234,0x800,0x100000)/File(\EFI\ubuntu\shimx64.efi)"


def _make_entry(**overrides: object) -> BootEntry:
    defaults: dict[str, object] = {
        "boot_number": "0000",
        "label": "ubuntu",
        "active": True,
        "device_path": _DEVICE_PATH,
        "raw_line": f"Boot0000* ubuntu\t{_DEVICE_PATH}",
    }
    defaults.update(overrides)
    return BootEntry(**defaults)  # type: ignore[arg-type]


def _make_configuration(**overrides: object) -> FirmwareBootConfiguration:
    defaults: dict[str, object] = {
        "current_boot_number": "0000",
        "timeout_seconds": 1,
        "boot_order": ("0000", "0001"),
        "boot_next": None,
        "entries": (
            _make_entry(),
            _make_entry(boot_number="0001", label="Windows Boot Manager"),
        ),
        "raw_text": "BootCurrent: 0000\nTimeout: 1 seconds\nBootOrder: 0000,0001\n",
    }
    defaults.update(overrides)
    return FirmwareBootConfiguration(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# BootEntry: construction / defaults
# ---------------------------------------------------------------------------


def test_boot_entry_construction_with_all_fields() -> None:
    entry = _make_entry()
    assert entry.boot_number == "0000"
    assert entry.label == "ubuntu"
    assert entry.active is True
    assert "shimx64.efi" in entry.device_path
    assert entry.raw_line.startswith("Boot0000*")


def test_boot_entry_device_path_may_be_empty_string() -> None:
    """A legitimate, if unusual, entry with no path segment."""
    entry = _make_entry(device_path="")
    assert entry.device_path == ""


def test_boot_entry_populate_by_name_accepts_camel_case_aliases() -> None:
    entry = BootEntry(
        bootNumber="00AB",
        label="recovery",
        active=False,
        devicePath="",
        rawLine="Boot00AB recovery",
    )
    assert entry.boot_number == "00AB"


# ---------------------------------------------------------------------------
# BootEntry: validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("boot_number", ["0000", "0A1b", "FFFF", "abcd"])
def test_boot_entry_accepts_valid_boot_number_formats(boot_number: str) -> None:
    entry = _make_entry(boot_number=boot_number)
    assert entry.boot_number == boot_number


@pytest.mark.parametrize("boot_number", ["000", "00000", "zzzz", "", "12-4", "0x00"])
def test_boot_entry_rejects_invalid_boot_number_formats(boot_number: str) -> None:
    with pytest.raises(ValidationError, match="four-hexadecimal-digit boot number"):
        _make_entry(boot_number=boot_number)


def test_boot_entry_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        BootEntry.model_validate(
            {
                "bootNumber": "0000",
                "label": "ubuntu",
                "active": True,
                "devicePath": "",
                "rawLine": "Boot0000 ubuntu",
                "bogus": 1,
            }
        )


def test_boot_entry_requires_all_fields() -> None:
    with pytest.raises(ValidationError):
        BootEntry.model_validate({"bootNumber": "0000"})


# ---------------------------------------------------------------------------
# BootEntry: immutability / equality / hashing
# ---------------------------------------------------------------------------


def test_boot_entry_is_frozen() -> None:
    entry = _make_entry()
    with pytest.raises(ValidationError):
        entry.label = "changed"  # type: ignore[misc]


def test_boot_entry_equality() -> None:
    assert _make_entry() == _make_entry()
    assert _make_entry(label="ubuntu") != _make_entry(label="fedora")


def test_boot_entry_is_hashable() -> None:
    assert isinstance(hash(_make_entry()), int)


# ---------------------------------------------------------------------------
# BootEntry: serialization / deserialization
# ---------------------------------------------------------------------------


def test_boot_entry_json_round_trip_uses_camel_case_aliases() -> None:
    entry = _make_entry()
    data = entry.model_dump(mode="json", by_alias=True)

    assert data["bootNumber"] == "0000"
    assert data["devicePath"] == entry.device_path
    assert data["rawLine"] == entry.raw_line
    assert "boot_number" not in data

    reloaded = BootEntry.model_validate(data)
    assert reloaded == entry


# ---------------------------------------------------------------------------
# FirmwareBootConfiguration: construction / defaults
# ---------------------------------------------------------------------------


def test_configuration_construction_with_all_fields() -> None:
    config = _make_configuration()
    assert config.current_boot_number == "0000"
    assert config.timeout_seconds == 1
    assert config.boot_order == ("0000", "0001")
    assert config.boot_next is None
    assert len(config.entries) == 2
    assert config.entries[0].boot_number == "0000"


def test_configuration_minimal_defaults() -> None:
    """Only raw_text is required; every other field has a sensible default
    representing 'absent from the source text.'
    """
    config = FirmwareBootConfiguration(raw_text="")
    assert config.current_boot_number is None
    assert config.timeout_seconds is None
    assert config.boot_order == ()
    assert config.boot_next is None
    assert config.entries == ()
    assert config.raw_text == ""


def test_configuration_entries_preserve_source_order_not_boot_order() -> None:
    """entries are never reordered to match boot_order - see docs/EFI_ADAPTER.md."""
    config = _make_configuration(
        boot_order=("0001", "0000"),
        entries=(
            _make_entry(boot_number="0000"),
            _make_entry(boot_number="0001"),
        ),
    )
    assert [entry.boot_number for entry in config.entries] == ["0000", "0001"]
    assert config.boot_order == ("0001", "0000")


def test_configuration_populate_by_name_accepts_camel_case_aliases() -> None:
    config = FirmwareBootConfiguration(
        currentBootNumber="0000",
        timeoutSeconds=5,
        bootOrder=("0000",),
        bootNext=None,
        entries=(_make_entry(),),
        rawText="...",
    )
    assert config.current_boot_number == "0000"


# ---------------------------------------------------------------------------
# FirmwareBootConfiguration: validation
# ---------------------------------------------------------------------------


def test_configuration_rejects_invalid_current_boot_number() -> None:
    with pytest.raises(ValidationError, match="four-hexadecimal-digit boot number"):
        _make_configuration(current_boot_number="not-hex")


def test_configuration_rejects_invalid_boot_next() -> None:
    with pytest.raises(ValidationError, match="four-hexadecimal-digit boot number"):
        _make_configuration(boot_next="zzzz")


def test_configuration_accepts_valid_boot_next() -> None:
    config = _make_configuration(boot_next="0001")
    assert config.boot_next == "0001"


def test_configuration_rejects_invalid_boot_order_entry() -> None:
    with pytest.raises(ValidationError, match="four-hexadecimal-digit boot number"):
        _make_configuration(boot_order=("0000", "bogus"))


def test_configuration_rejects_negative_timeout() -> None:
    with pytest.raises(ValidationError):
        _make_configuration(timeout_seconds=-1)


def test_configuration_accepts_zero_timeout() -> None:
    config = _make_configuration(timeout_seconds=0)
    assert config.timeout_seconds == 0


def test_configuration_rejects_duplicate_entry_boot_numbers() -> None:
    with pytest.raises(ValidationError, match="duplicate boot_number"):
        _make_configuration(
            entries=(
                _make_entry(boot_number="0000", label="ubuntu"),
                _make_entry(boot_number="0000", label="duplicate"),
            )
        )


def test_configuration_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        FirmwareBootConfiguration.model_validate({"rawText": "", "bogus": 1})


def test_configuration_requires_raw_text() -> None:
    with pytest.raises(ValidationError):
        FirmwareBootConfiguration.model_validate({})


# ---------------------------------------------------------------------------
# FirmwareBootConfiguration: immutability / equality / hashing
# ---------------------------------------------------------------------------


def test_configuration_is_frozen() -> None:
    config = _make_configuration()
    with pytest.raises(ValidationError):
        config.timeout_seconds = 99  # type: ignore[misc]


def test_configuration_nested_entry_is_frozen() -> None:
    config = _make_configuration()
    with pytest.raises(ValidationError):
        config.entries[0].label = "changed"  # type: ignore[misc]


def test_configuration_equality() -> None:
    assert _make_configuration() == _make_configuration()
    assert _make_configuration(timeout_seconds=1) != _make_configuration(timeout_seconds=2)


def test_configuration_is_hashable() -> None:
    """Unlike HostInventory (which has list fields), every container field
    here is a tuple of hashable items, so the whole frozen model is
    hashable too.
    """
    assert isinstance(hash(_make_configuration()), int)


# ---------------------------------------------------------------------------
# FirmwareBootConfiguration: serialization / deserialization
# ---------------------------------------------------------------------------


def test_configuration_json_round_trip_uses_camel_case_aliases() -> None:
    config = _make_configuration()
    data = config.model_dump(mode="json", by_alias=True)

    assert data["currentBootNumber"] == "0000"
    assert data["timeoutSeconds"] == 1
    assert data["bootOrder"] == ["0000", "0001"]
    assert data["bootNext"] is None
    assert data["rawText"] == config.raw_text
    assert data["entries"][0]["bootNumber"] == "0000"
    assert "current_boot_number" not in data

    reloaded = FirmwareBootConfiguration.model_validate(data)
    assert reloaded == config


def test_configuration_json_round_trip_with_minimal_defaults() -> None:
    config = FirmwareBootConfiguration(raw_text="unparseable garbage")
    data = config.model_dump(mode="json", by_alias=True)
    assert data["bootOrder"] == []
    assert data["entries"] == []

    reloaded = FirmwareBootConfiguration.model_validate(data)
    assert reloaded == config
