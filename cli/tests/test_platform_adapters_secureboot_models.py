from __future__ import annotations

import pytest
from pydantic import ValidationError

from bcs.platform.adapters.secureboot.models import SecureBootState, SecureBootStatus


def _make_status(**overrides: object) -> SecureBootStatus:
    defaults: dict[str, object] = {
        "state": SecureBootState.ENABLED,
        "setup_mode": False,
        "raw_text": "SecureBoot enabled\nSetupMode disabled\n",
    }
    defaults.update(overrides)
    return SecureBootStatus(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# SecureBootState
# ---------------------------------------------------------------------------


def test_secure_boot_state_has_four_values() -> None:
    assert {member.value for member in SecureBootState} == {
        "enabled",
        "disabled",
        "unsupported",
        "unknown",
    }


def test_secure_boot_state_is_independently_defined_from_inventory_enum() -> None:
    """Deliberately a separate type from bcs.inventory.models.SecureBootState -
    see docs/SECURE_BOOT_ADAPTER.md#naming-rationale.
    """
    from bcs.inventory.models import SecureBootState as InventorySecureBootState

    assert SecureBootState is not InventorySecureBootState
    assert {m.value for m in SecureBootState} == {m.value for m in InventorySecureBootState}


# ---------------------------------------------------------------------------
# SecureBootStatus: construction / defaults
# ---------------------------------------------------------------------------


def test_status_construction_with_all_fields() -> None:
    status = _make_status()
    assert status.state == SecureBootState.ENABLED
    assert status.setup_mode is False
    assert status.raw_text == "SecureBoot enabled\nSetupMode disabled\n"


def test_status_minimal_defaults() -> None:
    """Only state and raw_text are required; setup_mode defaults to None,
    meaning 'not reported by the source text' - see docs/SECURE_BOOT_ADAPTER.md.
    """
    status = SecureBootStatus(state=SecureBootState.UNKNOWN, raw_text="")
    assert status.state == SecureBootState.UNKNOWN
    assert status.setup_mode is None
    assert status.raw_text == ""


@pytest.mark.parametrize(
    "state",
    [
        SecureBootState.ENABLED,
        SecureBootState.DISABLED,
        SecureBootState.UNSUPPORTED,
        SecureBootState.UNKNOWN,
    ],
)
def test_status_accepts_every_state(state: SecureBootState) -> None:
    status = _make_status(state=state)
    assert status.state == state


def test_status_populate_by_name_accepts_camel_case_alias() -> None:
    status = SecureBootStatus(
        state=SecureBootState.DISABLED,
        setupMode=True,
        rawText="SecureBoot disabled\nSetupMode enabled\n",
    )
    assert status.setup_mode is True


# ---------------------------------------------------------------------------
# SecureBootStatus: validation
# ---------------------------------------------------------------------------


def test_status_rejects_invalid_state_value() -> None:
    with pytest.raises(ValidationError):
        SecureBootStatus.model_validate({"state": "bogus", "rawText": ""})


def test_status_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        SecureBootStatus.model_validate(
            {
                "state": "enabled",
                "setupMode": False,
                "rawText": "SecureBoot enabled\n",
                "bogus": 1,
            }
        )


def test_status_requires_state() -> None:
    with pytest.raises(ValidationError):
        SecureBootStatus.model_validate({"rawText": ""})


def test_status_requires_raw_text() -> None:
    with pytest.raises(ValidationError):
        SecureBootStatus.model_validate({"state": "enabled"})


# ---------------------------------------------------------------------------
# SecureBootStatus: immutability / equality / hashing
# ---------------------------------------------------------------------------


def test_status_is_frozen() -> None:
    status = _make_status()
    with pytest.raises(ValidationError):
        status.state = SecureBootState.DISABLED  # type: ignore[misc]


def test_status_equality() -> None:
    assert _make_status() == _make_status()
    assert _make_status(state=SecureBootState.ENABLED) != _make_status(
        state=SecureBootState.DISABLED
    )


def test_status_is_hashable() -> None:
    assert isinstance(hash(_make_status()), int)


# ---------------------------------------------------------------------------
# SecureBootStatus: serialization / deserialization
# ---------------------------------------------------------------------------


def test_status_json_round_trip_uses_camel_case_aliases() -> None:
    status = _make_status()
    data = status.model_dump(mode="json", by_alias=True)

    assert data["state"] == "enabled"
    assert data["setupMode"] is False
    assert data["rawText"] == status.raw_text
    assert "setup_mode" not in data

    reloaded = SecureBootStatus.model_validate(data)
    assert reloaded == status


def test_status_json_round_trip_with_minimal_defaults() -> None:
    status = SecureBootStatus(state=SecureBootState.UNSUPPORTED, raw_text="")
    data = status.model_dump(mode="json", by_alias=True)
    assert data["setupMode"] is None

    reloaded = SecureBootStatus.model_validate(data)
    assert reloaded == status
