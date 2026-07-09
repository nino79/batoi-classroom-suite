"""Tests for the Secure Boot Adapter orchestration layer.

These tests verify that ``read_secure_boot_status``:
- Invokes the correct command (``["mokutil", "--sb-state"]``) with
  correct locale-forced environment.
- Forwards the timeout parameter correctly, defaulting to 5.0 seconds.
- Returns a correctly-parsed ``SecureBootStatus`` on success.
- Propagates ``CommandNotFoundError`` and ``CommandTimeoutError`` from
  the runner unchanged.
- Raises ``SecureBootUnavailableError`` for non-zero exits whose
  stderr is recognisably a "Secure Boot data unavailable" message.
- Raises ``SecureBootError`` for other non-zero exits.
- Raises ``SecureBootParseError`` when the command succeeds but the
  output cannot be parsed (a malformed field) or contains no
  recognized line at all.

A ``FakeCommandRunner`` is used instead of mocking
``SubprocessCommandRunner`` directly, so the tests exercise the
public ``CommandRunner`` interface rather than implementation details,
mirroring ``test_platform_adapters_efi_adapter.py``'s own style.
"""

from __future__ import annotations

import pytest
from tests.fake_command_runner import FakeCommandRunner, build_command_result

from bcs.platform.adapters.secureboot.adapter import read_secure_boot_status
from bcs.platform.adapters.secureboot.errors import (
    SecureBootError,
    SecureBootParseError,
    SecureBootUnavailableError,
)
from bcs.platform.adapters.secureboot.models import SecureBootState, SecureBootStatus
from bcs.platform.errors import CommandNotFoundError, CommandTimeoutError
from bcs.platform.execution import CommandRunner

# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------


def _sb_result(**kw: str | int) -> FakeCommandRunner:
    return FakeCommandRunner(
        result=build_command_result(command=("mokutil", "--sb-state"), **kw)  # type: ignore[arg-type]
    )


def test_calls_correct_command_with_locale_env() -> None:
    runner = _sb_result(stdout="SecureBoot enabled\n")
    read_secure_boot_status(runner)

    assert len(runner.calls) == 1
    call = runner.calls[0]
    assert call["command"] == ["mokutil", "--sb-state"]
    assert call["check"] is False
    # Locale must be forced to C for stable output
    assert call["env"]["LANG"] == "C"
    assert call["env"]["LC_ALL"] == "C"
    # PATH and other variables must still be present
    assert "PATH" in call["env"]


def test_default_timeout_is_five_seconds() -> None:
    runner = _sb_result(stdout="SecureBoot enabled\n")
    read_secure_boot_status(runner)

    assert runner.calls[0]["timeout_seconds"] == 5.0


def test_forwards_timeout_seconds() -> None:
    runner = _sb_result(stdout="SecureBoot enabled\n")
    read_secure_boot_status(runner, timeout_seconds=15.0)

    assert runner.calls[0]["timeout_seconds"] == 15.0


def test_timeout_none_is_forwarded() -> None:
    runner = _sb_result(stdout="SecureBoot enabled\n")
    read_secure_boot_status(runner, timeout_seconds=None)

    assert runner.calls[0]["timeout_seconds"] is None


def test_returns_parsed_secure_boot_status_enabled() -> None:
    runner = _sb_result(stdout="SecureBoot enabled\nSetupMode disabled\n")
    status = read_secure_boot_status(runner)

    assert isinstance(status, SecureBootStatus)
    assert status.state == SecureBootState.ENABLED
    assert status.setup_mode is False
    assert status.raw_text == "SecureBoot enabled\nSetupMode disabled\n"


def test_returns_parsed_secure_boot_status_disabled() -> None:
    runner = _sb_result(stdout="SecureBoot disabled\n")
    status = read_secure_boot_status(runner)

    assert status.state == SecureBootState.DISABLED
    assert status.setup_mode is None


def test_returns_parsed_secure_boot_status_setup_mode_enabled() -> None:
    runner = _sb_result(stdout="SecureBoot enabled\nSetupMode enabled\n")
    status = read_secure_boot_status(runner)

    assert status.state == SecureBootState.ENABLED
    assert status.setup_mode is True


# ---------------------------------------------------------------------------
# Platform error propagation
# ---------------------------------------------------------------------------


def test_command_not_found_propagates() -> None:
    runner = FakeCommandRunner(not_found_tools=frozenset({"mokutil"}))

    with pytest.raises(CommandNotFoundError):
        read_secure_boot_status(runner)


def test_command_timeout_propagates() -> None:
    runner = FakeCommandRunner(timeout_tools=frozenset({"mokutil"}))

    with pytest.raises(CommandTimeoutError):
        read_secure_boot_status(runner)


# ---------------------------------------------------------------------------
# Non-zero exit: unavailable vs. generic error
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "stderr",
    [
        "EFI variables are not supported on this system.",
        "This system doesn't support Secure Boot: not supported on this system",
        "Failed to read the SecureBoot variable: efivarfs not mounted",
        "mokutil: Permission denied",
        "mokutil: Operation not permitted",
        "mokutil: No such file or directory",
        "Failed to read SecureBoot-<GUID>",
    ],
)
def test_unavailable_error_for_recognised_stderr_patterns(stderr: str) -> None:
    runner = _sb_result(stderr=stderr, exit_code=1)

    with pytest.raises(SecureBootUnavailableError) as exc_info:
        read_secure_boot_status(runner)

    assert exc_info.value.result is not None
    assert exc_info.value.result.exit_code == 1


def test_generic_error_for_unrecognised_stderr() -> None:
    runner = _sb_result(stderr="something went wrong", exit_code=1)

    with pytest.raises(SecureBootError) as exc_info:
        read_secure_boot_status(runner)

    assert exc_info.value.result is not None
    assert exc_info.value.result.exit_code == 1
    # Must NOT be the more specific subclass
    assert not isinstance(exc_info.value, SecureBootUnavailableError)


# ---------------------------------------------------------------------------
# Parser failure
# ---------------------------------------------------------------------------


def test_parse_error_for_malformed_field() -> None:
    runner = _sb_result(stdout="SecureBoot maybe\n")

    with pytest.raises(SecureBootParseError) as exc_info:
        read_secure_boot_status(runner)

    assert exc_info.value.text == "SecureBoot maybe\n"


def test_parse_error_when_no_recognized_line_at_all() -> None:
    # The parser itself tolerates this (returns state=UNKNOWN,
    # setup_mode=None) - it is this adapter's own judgment that
    # "nothing recognized at all" is a parse failure, not a legitimate
    # UNKNOWN result, per docs/SECURE_BOOT_ADAPTER.md#adapter-responsibilities
    # point 4.
    runner = _sb_result(stdout="some unrelated banner text\n")

    with pytest.raises(SecureBootParseError) as exc_info:
        read_secure_boot_status(runner)

    assert exc_info.value.text == "some unrelated banner text\n"


def test_parse_error_for_completely_empty_output() -> None:
    runner = _sb_result(stdout="")

    with pytest.raises(SecureBootParseError):
        read_secure_boot_status(runner)


def test_no_parse_error_when_only_setup_mode_recognized() -> None:
    # state stays UNKNOWN (no SecureBoot line), but setup_mode is not
    # None - at least one line was recognized, so this is NOT treated
    # as "no recognized line at all".
    runner = _sb_result(stdout="SetupMode disabled\n")

    status = read_secure_boot_status(runner)

    assert status.state == SecureBootState.UNKNOWN
    assert status.setup_mode is False


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


def test_fake_command_runner_satisfies_protocol() -> None:
    runner = _sb_result(stdout="SecureBoot enabled\n")
    # isinstance check against the runtime-checkable Protocol
    assert isinstance(runner, CommandRunner)
