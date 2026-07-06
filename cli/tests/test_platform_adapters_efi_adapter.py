"""Tests for the EFI Adapter orchestration layer.

These tests verify that ``read_firmware_boot_configuration``:
- Invokes the correct command with correct locale-forced environment.
- Forwards the timeout parameter correctly.
- Returns a correctly-parsed ``FirmwareBootConfiguration`` on success.
- Propagates ``CommandNotFoundError`` and ``CommandTimeoutError`` from
  the runner unchanged.
- Raises ``FirmwareBootUnavailableError`` for non-zero exits whose
  stderr is recognisably an "EFI variables unavailable" message.
- Raises ``FirmwareBootError`` for other non-zero exits.
- Raises ``FirmwareBootParseError`` when the command succeeds but the
  output cannot be parsed.

A ``FakeCommandRunner`` is used instead of mocking
``SubprocessCommandRunner`` directly, so the tests exercise the
public ``CommandRunner`` interface rather than implementation details.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest

from bcs.platform.adapters.efi.adapter import read_firmware_boot_configuration
from bcs.platform.adapters.efi.errors import (
    FirmwareBootError,
    FirmwareBootParseError,
    FirmwareBootUnavailableError,
)
from bcs.platform.adapters.efi.models import FirmwareBootConfiguration
from bcs.platform.errors import CommandNotFoundError, CommandTimeoutError
from bcs.platform.execution import CommandRunner


# ---------------------------------------------------------------------------
# Fake CommandRunner
# ---------------------------------------------------------------------------


@dataclass
class FakeCommandResult:
    """A minimal stand-in for ``CommandResult`` used in these tests."""

    command: tuple[str, ...]
    stdout: str
    stderr: str
    exit_code: int
    duration: float
    started_at: datetime
    finished_at: datetime
    working_directory: str | None = None
    timed_out: bool = False

    def to_result(self) -> MagicMock:
        m = MagicMock()
        m.command = self.command
        m.stdout = self.stdout
        m.stderr = self.stderr
        m.exit_code = self.exit_code
        m.duration = self.duration
        m.started_at = self.started_at
        m.finished_at = self.finished_at
        m.working_directory = self.working_directory
        m.timed_out = self.timed_out
        return m


@dataclass
class FakeCommandRunner:
    """A configurable ``CommandRunner`` stand-in for testing.

    Set ``raise_not_found`` or ``raise_timeout`` to simulate those
    runner-level exceptions.  Otherwise ``result`` (a
    ``FakeCommandResult``) is returned on every call.
    """

    result: FakeCommandResult | None = None
    raise_not_found: bool = False
    raise_timeout: bool = False
    calls: list[dict[str, Any]] = field(default_factory=list)

    def run(
        self,
        command: Any,
        *,
        timeout_seconds: Any = None,
        check: bool = False,
        cwd: Any = None,
        env: Any = None,
        input_text: Any = None,
    ) -> MagicMock:
        self.calls.append(
            {
                "command": command,
                "timeout_seconds": timeout_seconds,
                "check": check,
                "cwd": cwd,
                "env": env,
                "input_text": input_text,
            }
        )
        if self.raise_not_found:
            raise CommandNotFoundError("efibootmgr not found", executable="efibootmgr")
        if self.raise_timeout:
            raise CommandTimeoutError(
                "efibootmgr timed out",
                partial_result=MagicMock(),
            )
        return self.result.to_result()


# ---------------------------------------------------------------------------
# Valid fixture text used across tests
# ---------------------------------------------------------------------------

_VALID_OUTPUT = (
    "BootCurrent: 0000\n"
    "Timeout: 5 seconds\n"
    "BootOrder: 0000,0001\n"
    "BootNext: 0001\n"
    "HD(1,GPT,aaaaaaaa-0000-0000-0000-000000000000,0x800,0x100000)"
    "/File(\\EFI\\ubuntu\\shimx64.efi)\n"
    "Boot0000* ubuntu\n"
    "Boot0001* Windows Boot Manager\n"
    "HD(1,GPT,bbbbbbbb-0000-0000-0000-000000000000,0x800,0x100000)"
    "/File(\\EFI\\Microsoft\\Boot\\bootmgfw.efi)\n"
)


def _make_result(
    *,
    stdout: str = "",
    stderr: str = "",
    exit_code: int = 0,
) -> FakeCommandResult:
    now = datetime.now(tz=timezone.utc)
    return FakeCommandResult(
        command=("efibootmgr", "-v"),
        stdout=stdout,
        stderr=stderr,
        exit_code=exit_code,
        duration=0.1,
        started_at=now,
        finished_at=now,
    )


# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------


def test_calls_correct_command_with_locale_env() -> None:
    runner = FakeCommandRunner(result=_make_result(stdout=_VALID_OUTPUT))
    read_firmware_boot_configuration(runner)

    assert len(runner.calls) == 1
    call = runner.calls[0]
    assert call["command"] == ["efibootmgr", "-v"]
    assert call["check"] is False
    # Locale must be forced to C for stable output
    assert call["env"]["LANG"] == "C"
    assert call["env"]["LC_ALL"] == "C"
    # PATH and other variables must still be present
    assert "PATH" in call["env"]


def test_forwards_timeout_seconds() -> None:
    runner = FakeCommandRunner(result=_make_result(stdout=_VALID_OUTPUT))
    read_firmware_boot_configuration(runner, timeout_seconds=15.0)

    assert runner.calls[0]["timeout_seconds"] == 15.0


def test_timeout_none_is_forwarded() -> None:
    runner = FakeCommandRunner(result=_make_result(stdout=_VALID_OUTPUT))
    read_firmware_boot_configuration(runner, timeout_seconds=None)

    assert runner.calls[0]["timeout_seconds"] is None


def test_returns_parsed_firmware_boot_configuration() -> None:
    runner = FakeCommandRunner(result=_make_result(stdout=_VALID_OUTPUT))
    config = read_firmware_boot_configuration(runner)

    assert isinstance(config, FirmwareBootConfiguration)
    assert config.current_boot_number == "0000"
    assert config.timeout_seconds == 5
    assert config.boot_order == ("0000", "0001")
    assert config.boot_next == "0001"
    assert len(config.entries) == 2
    assert config.entries[0].boot_number == "0000"
    assert config.entries[0].label == "ubuntu"
    assert config.entries[1].boot_number == "0001"
    assert config.entries[1].label == "Windows Boot Manager"


# ---------------------------------------------------------------------------
# Platform error propagation
# ---------------------------------------------------------------------------


def test_command_not_found_propagates() -> None:
    runner = FakeCommandRunner(raise_not_found=True)

    with pytest.raises(CommandNotFoundError):
        read_firmware_boot_configuration(runner)


def test_command_timeout_propagates() -> None:
    runner = FakeCommandRunner(raise_timeout=True)

    with pytest.raises(CommandTimeoutError):
        read_firmware_boot_configuration(runner)


# ---------------------------------------------------------------------------
# Non-zero exit: unavailable vs. generic error
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "stderr",
    [
        "EFI variables are not available: efivars not mounted.",
        "Could not open efivarfs: Permission denied",
        "efibootmgr: BootVariable: Operation not permitted",
        "efibootmgr: Read boot entries: No such file or directory",
        "EFI System Partition not found.",
        "efibootmgr: unable to communicate with boot variable",
        "This system does not support EFI boot variables.",
    ],
)
def test_unavailable_error_for_recognised_stderr_patterns(stderr: str) -> None:
    runner = FakeCommandRunner(
        result=_make_result(stderr=stderr, exit_code=1)
    )

    with pytest.raises(FirmwareBootUnavailableError) as exc_info:
        read_firmware_boot_configuration(runner)

    assert exc_info.value.result is not None
    assert exc_info.value.result.exit_code == 1


def test_generic_error_for_unrecognised_stderr() -> None:
    runner = FakeCommandRunner(
        result=_make_result(stderr="something went wrong", exit_code=1)
    )

    with pytest.raises(FirmwareBootError) as exc_info:
        read_firmware_boot_configuration(runner)

    assert exc_info.value.result is not None
    assert exc_info.value.result.exit_code == 1
    # Must NOT be the more specific subclass
    assert not isinstance(exc_info.value, FirmwareBootUnavailableError)


# ---------------------------------------------------------------------------
# Parser failure
# ---------------------------------------------------------------------------


def test_parse_error_when_output_is_unrecognisable() -> None:
    # The parser silently ignores lines it doesn't recognise (permissive by
    # default).  To trigger FirmwareBootParseError the output must match a
    # recognised prefix but contain an invalid value for that field.
    runner = FakeCommandRunner(
        result=_make_result(stdout="BootCurrent: ZZ\n")
    )

    with pytest.raises(FirmwareBootParseError) as exc_info:
        read_firmware_boot_configuration(runner)

    assert exc_info.value.text == "BootCurrent: ZZ\n"


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


def test_fake_command_runner_satisfies_protocol() -> None:
    runner = FakeCommandRunner(result=_make_result(stdout=_VALID_OUTPUT))
    # isinstance check against the runtime-checkable Protocol
    assert isinstance(runner, CommandRunner)