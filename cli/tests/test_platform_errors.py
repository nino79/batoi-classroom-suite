from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from bcs.errors import BcsError
from bcs.platform.errors import (
    CommandExecutionError,
    CommandNotFoundError,
    CommandTimeoutError,
    PlatformError,
)
from bcs.platform.models import CommandResult

_STARTED = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
_FINISHED = _STARTED + timedelta(seconds=2)


def _make_result(**overrides: object) -> CommandResult:
    defaults: dict[str, object] = {
        "command": ("efibootmgr", "-v"),
        "stdout": "",
        "stderr": "",
        "exit_code": 1,
        "duration": 2.0,
        "started_at": _STARTED,
        "finished_at": _FINISHED,
        "timed_out": False,
    }
    defaults.update(overrides)
    return CommandResult(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# PlatformError (base)
# ---------------------------------------------------------------------------


def test_platform_error_is_an_exception() -> None:
    err = PlatformError("boom")
    assert isinstance(err, Exception)
    assert err.message == "boom"
    assert str(err) == "boom"


def test_platform_error_does_not_inherit_bcs_error() -> None:
    assert not issubclass(PlatformError, BcsError)


@pytest.mark.parametrize(
    "error_cls",
    [CommandNotFoundError, CommandTimeoutError, CommandExecutionError],
)
def test_every_subclass_is_a_platform_error_and_not_a_bcs_error(
    error_cls: type[PlatformError],
) -> None:
    assert issubclass(error_cls, PlatformError)
    assert not issubclass(error_cls, BcsError)


# ---------------------------------------------------------------------------
# CommandNotFoundError
# ---------------------------------------------------------------------------


def test_command_not_found_error_carries_executable() -> None:
    err = CommandNotFoundError("efibootmgr not found on PATH", executable="efibootmgr")
    assert err.message == "efibootmgr not found on PATH"
    assert err.executable == "efibootmgr"
    assert isinstance(err, PlatformError)


def test_command_not_found_error_is_raisable_and_catchable() -> None:
    with pytest.raises(CommandNotFoundError) as exc_info:
        raise CommandNotFoundError("nope", executable="rsync")
    assert exc_info.value.executable == "rsync"


def test_command_not_found_error_is_catchable_as_platform_error() -> None:
    with pytest.raises(PlatformError):
        raise CommandNotFoundError("nope", executable="rsync")


# ---------------------------------------------------------------------------
# CommandTimeoutError
# ---------------------------------------------------------------------------


def test_command_timeout_error_carries_partial_result() -> None:
    partial = _make_result(exit_code=None, timed_out=True)
    err = CommandTimeoutError("timed out after 5s", partial_result=partial)
    assert err.message == "timed out after 5s"
    assert err.partial_result is partial
    assert err.partial_result.timed_out is True
    assert err.partial_result.exit_code is None


def test_command_timeout_error_is_raisable_and_catchable() -> None:
    partial = _make_result(exit_code=None, timed_out=True)
    with pytest.raises(CommandTimeoutError) as exc_info:
        raise CommandTimeoutError("timed out", partial_result=partial)
    assert exc_info.value.partial_result.timed_out is True


# ---------------------------------------------------------------------------
# CommandExecutionError
# ---------------------------------------------------------------------------


def test_command_execution_error_carries_result() -> None:
    result = _make_result(exit_code=1)
    err = CommandExecutionError("command exited non-zero", result=result)
    assert err.message == "command exited non-zero"
    assert err.result is result
    assert err.result.exit_code == 1
    assert err.result.success is False


def test_command_execution_error_is_raisable_and_catchable() -> None:
    result = _make_result(exit_code=127)
    with pytest.raises(CommandExecutionError) as exc_info:
        raise CommandExecutionError("failed", result=result)
    assert exc_info.value.result.exit_code == 127
