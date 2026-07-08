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

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

import pytest

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
    runner-level exceptions. Otherwise ``result`` (a
    ``FakeCommandResult``) is returned on every call.
    """

    result: FakeCommandResult | None = None
    raise_not_found: bool = False
    raise_timeout: bool = False
    calls: list[dict[str, Any]] = field(default_factory=list)

    def run(  # noqa: PLR0913 - mirrors CommandRunner.run()'s own protocol signature
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
            raise CommandNotFoundError("mokutil not found", executable="mokutil")
        if self.raise_timeout:
            raise CommandTimeoutError(
                "mokutil timed out",
                partial_result=MagicMock(),
            )
        return self.result.to_result()


def _make_result(
    *,
    stdout: str = "",
    stderr: str = "",
    exit_code: int = 0,
) -> FakeCommandResult:
    now = datetime.now(tz=UTC)
    return FakeCommandResult(
        command=("mokutil", "--sb-state"),
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
    runner = FakeCommandRunner(result=_make_result(stdout="SecureBoot enabled\n"))
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
    runner = FakeCommandRunner(result=_make_result(stdout="SecureBoot enabled\n"))
    read_secure_boot_status(runner)

    assert runner.calls[0]["timeout_seconds"] == 5.0


def test_forwards_timeout_seconds() -> None:
    runner = FakeCommandRunner(result=_make_result(stdout="SecureBoot enabled\n"))
    read_secure_boot_status(runner, timeout_seconds=15.0)

    assert runner.calls[0]["timeout_seconds"] == 15.0


def test_timeout_none_is_forwarded() -> None:
    runner = FakeCommandRunner(result=_make_result(stdout="SecureBoot enabled\n"))
    read_secure_boot_status(runner, timeout_seconds=None)

    assert runner.calls[0]["timeout_seconds"] is None


def test_returns_parsed_secure_boot_status_enabled() -> None:
    runner = FakeCommandRunner(
        result=_make_result(stdout="SecureBoot enabled\nSetupMode disabled\n")
    )
    status = read_secure_boot_status(runner)

    assert isinstance(status, SecureBootStatus)
    assert status.state == SecureBootState.ENABLED
    assert status.setup_mode is False
    assert status.raw_text == "SecureBoot enabled\nSetupMode disabled\n"


def test_returns_parsed_secure_boot_status_disabled() -> None:
    runner = FakeCommandRunner(result=_make_result(stdout="SecureBoot disabled\n"))
    status = read_secure_boot_status(runner)

    assert status.state == SecureBootState.DISABLED
    assert status.setup_mode is None


def test_returns_parsed_secure_boot_status_setup_mode_enabled() -> None:
    runner = FakeCommandRunner(
        result=_make_result(stdout="SecureBoot enabled\nSetupMode enabled\n")
    )
    status = read_secure_boot_status(runner)

    assert status.state == SecureBootState.ENABLED
    assert status.setup_mode is True


# ---------------------------------------------------------------------------
# Platform error propagation
# ---------------------------------------------------------------------------


def test_command_not_found_propagates() -> None:
    runner = FakeCommandRunner(raise_not_found=True)

    with pytest.raises(CommandNotFoundError):
        read_secure_boot_status(runner)


def test_command_timeout_propagates() -> None:
    runner = FakeCommandRunner(raise_timeout=True)

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
    runner = FakeCommandRunner(result=_make_result(stderr=stderr, exit_code=1))

    with pytest.raises(SecureBootUnavailableError) as exc_info:
        read_secure_boot_status(runner)

    assert exc_info.value.result is not None
    assert exc_info.value.result.exit_code == 1


def test_generic_error_for_unrecognised_stderr() -> None:
    runner = FakeCommandRunner(result=_make_result(stderr="something went wrong", exit_code=1))

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
    runner = FakeCommandRunner(result=_make_result(stdout="SecureBoot maybe\n"))

    with pytest.raises(SecureBootParseError) as exc_info:
        read_secure_boot_status(runner)

    assert exc_info.value.text == "SecureBoot maybe\n"


def test_parse_error_when_no_recognized_line_at_all() -> None:
    # The parser itself tolerates this (returns state=UNKNOWN,
    # setup_mode=None) - it is this adapter's own judgment that
    # "nothing recognized at all" is a parse failure, not a legitimate
    # UNKNOWN result, per docs/SECURE_BOOT_ADAPTER.md#adapter-responsibilities
    # point 4.
    runner = FakeCommandRunner(result=_make_result(stdout="some unrelated banner text\n"))

    with pytest.raises(SecureBootParseError) as exc_info:
        read_secure_boot_status(runner)

    assert exc_info.value.text == "some unrelated banner text\n"


def test_parse_error_for_completely_empty_output() -> None:
    runner = FakeCommandRunner(result=_make_result(stdout=""))

    with pytest.raises(SecureBootParseError):
        read_secure_boot_status(runner)


def test_no_parse_error_when_only_setup_mode_recognized() -> None:
    # state stays UNKNOWN (no SecureBoot line), but setup_mode is not
    # None - at least one line was recognized, so this is NOT treated
    # as "no recognized line at all".
    runner = FakeCommandRunner(result=_make_result(stdout="SetupMode disabled\n"))

    status = read_secure_boot_status(runner)

    assert status.state == SecureBootState.UNKNOWN
    assert status.setup_mode is False


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


def test_fake_command_runner_satisfies_protocol() -> None:
    runner = FakeCommandRunner(result=_make_result(stdout="SecureBoot enabled\n"))
    # isinstance check against the runtime-checkable Protocol
    assert isinstance(runner, CommandRunner)
