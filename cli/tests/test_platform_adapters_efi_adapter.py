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

import pytest
from tests.fake_command_runner import FakeCommandRunner, build_command_result

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


# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------


def _efi_result(**kw: str | int) -> FakeCommandRunner:
    return FakeCommandRunner(
        result=build_command_result(command=("efibootmgr", "-v"), **kw)  # type: ignore[arg-type]
    )


def test_calls_correct_command_with_locale_env() -> None:
    runner = _efi_result(stdout=_VALID_OUTPUT)
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
    runner = _efi_result(stdout=_VALID_OUTPUT)
    read_firmware_boot_configuration(runner, timeout_seconds=15.0)

    assert runner.calls[0]["timeout_seconds"] == 15.0


def test_timeout_none_is_forwarded() -> None:
    runner = _efi_result(stdout=_VALID_OUTPUT)
    read_firmware_boot_configuration(runner, timeout_seconds=None)

    assert runner.calls[0]["timeout_seconds"] is None


def test_returns_parsed_firmware_boot_configuration() -> None:
    runner = _efi_result(stdout=_VALID_OUTPUT)
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
    runner = FakeCommandRunner(not_found_tools=frozenset({"efibootmgr"}))

    with pytest.raises(CommandNotFoundError):
        read_firmware_boot_configuration(runner)


def test_command_timeout_propagates() -> None:
    runner = FakeCommandRunner(timeout_tools=frozenset({"efibootmgr"}))

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
    runner = _efi_result(stderr=stderr, exit_code=1)

    with pytest.raises(FirmwareBootUnavailableError) as exc_info:
        read_firmware_boot_configuration(runner)

    assert exc_info.value.result is not None
    assert exc_info.value.result.exit_code == 1


def test_generic_error_for_unrecognised_stderr() -> None:
    runner = _efi_result(stderr="something went wrong", exit_code=1)

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
    runner = _efi_result(stdout="BootCurrent: ZZ\n")

    with pytest.raises(FirmwareBootParseError) as exc_info:
        read_firmware_boot_configuration(runner)

    assert exc_info.value.text == "BootCurrent: ZZ\n"


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


def test_fake_command_runner_satisfies_protocol() -> None:
    runner = _efi_result(stdout=_VALID_OUTPUT)
    # isinstance check against the runtime-checkable Protocol
    assert isinstance(runner, CommandRunner)
