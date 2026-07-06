from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from bcs.platform.models import CommandResult

_STARTED = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
_FINISHED = _STARTED + timedelta(seconds=2)


def _make_result(**overrides: object) -> CommandResult:
    defaults: dict[str, object] = {
        "command": ("efibootmgr", "-v"),
        "stdout": "BootCurrent: 0001\n",
        "stderr": "",
        "exit_code": 0,
        "duration": 2.0,
        "started_at": _STARTED,
        "finished_at": _FINISHED,
        "timed_out": False,
    }
    defaults.update(overrides)
    return CommandResult(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# construction / defaults
# ---------------------------------------------------------------------------


def test_construction_with_required_fields_only() -> None:
    result = _make_result()
    assert result.command == ("efibootmgr", "-v")
    assert result.working_directory is None


def test_working_directory_can_be_set() -> None:
    result = _make_result(working_directory="/opt/bcs")
    assert result.working_directory == "/opt/bcs"


def test_populate_by_name_accepts_snake_case_kwargs() -> None:
    result = _make_result(exit_code=0)
    assert result.exit_code == 0


def test_populate_by_name_accepts_camel_case_aliases() -> None:
    result = CommandResult(
        command=("true",),
        stdout="",
        stderr="",
        exitCode=0,
        duration=0.1,
        startedAt=_STARTED,
        finishedAt=_FINISHED,
        timedOut=False,
    )
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# success
# ---------------------------------------------------------------------------


def test_success_true_on_zero_exit_code() -> None:
    assert _make_result(exit_code=0).success is True


def test_success_false_on_nonzero_exit_code() -> None:
    assert _make_result(exit_code=1).success is False


def test_success_false_when_timed_out() -> None:
    result = _make_result(exit_code=None, timed_out=True)
    assert result.success is False


def test_success_is_not_a_serialized_field() -> None:
    data = _make_result().model_dump(mode="json", by_alias=True)
    assert "success" not in data


# ---------------------------------------------------------------------------
# the exit_code / timed_out invariant
# ---------------------------------------------------------------------------


def test_timed_out_requires_exit_code_none() -> None:
    with pytest.raises(ValidationError, match="exit_code must be None"):
        _make_result(exit_code=1, timed_out=True)


def test_not_timed_out_requires_exit_code_present() -> None:
    with pytest.raises(ValidationError, match="exit_code is required"):
        _make_result(exit_code=None, timed_out=False)


def test_timed_out_with_exit_code_none_is_valid() -> None:
    result = _make_result(exit_code=None, timed_out=True)
    assert result.timed_out is True
    assert result.exit_code is None


# ---------------------------------------------------------------------------
# other validation
# ---------------------------------------------------------------------------


def test_finished_at_before_started_at_is_rejected() -> None:
    with pytest.raises(ValidationError, match="finished_at must not be before started_at"):
        _make_result(started_at=_FINISHED, finished_at=_STARTED)


def test_finished_at_equal_to_started_at_is_valid() -> None:
    result = _make_result(started_at=_STARTED, finished_at=_STARTED, duration=0.0)
    assert result.duration == 0.0


def test_empty_command_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _make_result(command=())


def test_negative_duration_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _make_result(duration=-0.5)


# ---------------------------------------------------------------------------
# immutability
# ---------------------------------------------------------------------------


def test_model_is_frozen() -> None:
    result = _make_result()
    with pytest.raises(ValidationError):
        result.exit_code = 1  # type: ignore[misc]


def test_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        CommandResult.model_validate(
            {
                "command": ["true"],
                "stdout": "",
                "stderr": "",
                "exitCode": 0,
                "duration": 0.1,
                "startedAt": _STARTED.isoformat(),
                "finishedAt": _FINISHED.isoformat(),
                "timedOut": False,
                "bogus": 1,
            }
        )


def test_is_hashable() -> None:
    """Unlike HostInventory (which has list fields), every CommandResult
    field is itself hashable (command is a tuple, not a list), so the
    whole frozen model is hashable too.
    """
    assert isinstance(hash(_make_result()), int)


# ---------------------------------------------------------------------------
# JSON round-trip
# ---------------------------------------------------------------------------


def test_json_round_trip_uses_camel_case_aliases() -> None:
    result = _make_result(working_directory="/srv")
    data = result.model_dump(mode="json", by_alias=True)

    assert data["exitCode"] == 0
    assert data["startedAt"] == "2026-01-01T12:00:00Z"
    assert data["finishedAt"] == "2026-01-01T12:00:02Z"
    assert data["workingDirectory"] == "/srv"
    assert data["timedOut"] is False
    assert data["command"] == ["efibootmgr", "-v"]

    reloaded = CommandResult.model_validate(data)
    assert reloaded == result


def test_json_round_trip_for_timed_out_result() -> None:
    result = _make_result(exit_code=None, timed_out=True)
    data = result.model_dump(mode="json", by_alias=True)
    assert data["exitCode"] is None
    assert data["timedOut"] is True

    reloaded = CommandResult.model_validate(data)
    assert reloaded == result
