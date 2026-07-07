"""Unit tests for ``bcs.platform.adapters.secureboot.errors``.

Exhaustive coverage of the Secure Boot Adapter's error hierarchy:
``SecureBootError``, ``SecureBootUnavailableError``, and
``SecureBootParseError``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from bcs.platform.adapters.secureboot.errors import (
    SecureBootError,
    SecureBootParseError,
    SecureBootUnavailableError,
)
from bcs.platform.errors import PlatformError
from bcs.platform.models import CommandResult

# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


def _make_result(**overrides: Any) -> CommandResult:
    """Return a reproducible ``CommandResult`` for deterministic tests."""
    defaults: dict[str, Any] = {
        "command": ("mokutil", "--sb-state"),
        "stdout": "",
        "stderr": "",
        "exit_code": 0,
        "duration": 0.05,
        "started_at": datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        "finished_at": datetime(2025, 1, 1, 12, 0, 0, 50_000, tzinfo=UTC),
        "timed_out": False,
    }
    defaults.update(overrides)
    return CommandResult.model_validate(defaults)


# ---------------------------------------------------------------------------
# SecureBootError
# ---------------------------------------------------------------------------


class TestSecureBootError:
    """Tests for the ``SecureBootError`` base exception."""

    def test_message_is_stored(self) -> None:
        err = SecureBootError("mokutil exited with code 2")
        assert err.message == "mokutil exited with code 2"

    def test_message_is_exception_arg(self) -> None:
        err = SecureBootError("mokutil exited with code 2")
        assert str(err) == "mokutil exited with code 2"

    def test_inherits_from_platform_error(self) -> None:
        assert issubclass(SecureBootError, PlatformError)

    def test_result_defaults_to_none(self) -> None:
        err = SecureBootError("something went wrong")
        assert err.result is None

    def test_result_can_be_set(self) -> None:
        result = _make_result()
        err = SecureBootError("mokutil failed", result=result)
        assert err.result is result

    def test_result_attribute_is_readable(self) -> None:
        result = _make_result(exit_code=1, stderr="SecureBoot is not supported")
        err = SecureBootError("mokutil failed", result=result)
        assert err.result is not None
        assert err.result.exit_code == 1
        assert err.result.stderr == "SecureBoot is not supported"

    def test_can_be_caught_as_platform_error(self) -> None:
        err = SecureBootError("mokutil failed")
        caught: PlatformError | None = None
        try:
            raise err
        except PlatformError as e:
            caught = e
        assert caught is err

    def test_can_be_caught_as_secure_boot_error(self) -> None:
        err = SecureBootError("mokutil failed")
        caught: SecureBootError | None = None
        try:
            raise err
        except SecureBootError as e:
            caught = e
        assert caught is err

    def test_multiple_instances_are_independent(self) -> None:
        err1 = SecureBootError("first error")
        err2 = SecureBootError("second error")
        assert err1.message != err2.message
        assert err1 is not err2


# ---------------------------------------------------------------------------
# SecureBootUnavailableError
# ---------------------------------------------------------------------------


class TestSecureBootUnavailableError:
    """Tests for ``SecureBootUnavailableError``."""

    def test_message_is_stored(self) -> None:
        err = SecureBootUnavailableError("mokutil not found")
        assert err.message == "mokutil not found"

    def test_inherits_from_secure_boot_error(self) -> None:
        assert issubclass(SecureBootUnavailableError, SecureBootError)

    def test_inherits_from_platform_error(self) -> None:
        assert issubclass(SecureBootUnavailableError, PlatformError)

    def test_result_defaults_to_none(self) -> None:
        err = SecureBootUnavailableError("mokutil not found")
        assert err.result is None

    def test_result_can_be_set(self) -> None:
        result = _make_result(exit_code=127, stderr="command not found")
        err = SecureBootUnavailableError("mokutil not found", result=result)
        assert err.result is result

    def test_can_be_caught_as_secure_boot_error(self) -> None:
        err = SecureBootUnavailableError("mokutil not found")
        caught: SecureBootError | None = None
        try:
            raise err
        except SecureBootError as e:
            caught = e
        assert caught is err

    def test_can_be_caught_as_platform_error(self) -> None:
        err = SecureBootUnavailableError("mokutil not found")
        caught: PlatformError | None = None
        try:
            raise err
        except PlatformError as e:
            caught = e
        assert caught is err

    def test_specific_use_case_tool_not_found(self) -> None:
        """Simulates the documented error: ``mokutil`` not found."""
        err = SecureBootUnavailableError("mokutil not found")
        assert "mokutil" in err.message
        assert "not found" in err.message

    def test_specific_use_case_permission_denied(self) -> None:
        """Simulates the documented error: permission denied querying firmware."""
        result = _make_result(exit_code=1, stderr="EFI variables not accessible")
        err = SecureBootUnavailableError(
            "cannot query Secure Boot state: permission denied", result=result
        )
        assert "permission denied" in err.message
        assert err.result is result

    def test_specific_use_case_unsupported_firmware(self) -> None:
        """Simulates the documented error: firmware does not support Secure Boot."""
        err = SecureBootUnavailableError("SecureBoot is not supported on this firmware")
        assert "not supported" in err.message


# ---------------------------------------------------------------------------
# SecureBootParseError
# ---------------------------------------------------------------------------


class TestSecureBootParseError:
    """Tests for ``SecureBootParseError``."""

    def test_message_is_stored(self) -> None:
        err = SecureBootParseError("malformed output", text="SecureBoot maybe\n")
        assert err.message == "malformed output"

    def test_inherits_from_secure_boot_error(self) -> None:
        assert issubclass(SecureBootParseError, SecureBootError)

    def test_inherits_from_platform_error(self) -> None:
        assert issubclass(SecureBootParseError, PlatformError)

    def test_text_attribute_is_set(self) -> None:
        bad_output = "SecureBoot maybe\n"
        err = SecureBootParseError("unrecognised state value", text=bad_output)
        assert err.text == bad_output

    def test_text_can_be_empty_string(self) -> None:
        err = SecureBootParseError("empty output", text="")
        assert err.text == ""

    def test_text_can_be_multiline(self) -> None:
        multiline = "line1\nline2\nline3"
        err = SecureBootParseError("not mokutil-shaped output", text=multiline)
        assert err.text == multiline

    def test_result_defaults_to_none(self) -> None:
        err = SecureBootParseError("parse failed", text="not mokutil output")
        assert err.result is None

    def test_can_be_caught_as_secure_boot_error(self) -> None:
        err = SecureBootParseError("parse failed", text="bad output")
        caught: SecureBootError | None = None
        try:
            raise err
        except SecureBootError as e:
            caught = e
        assert caught is err

    def test_can_be_caught_as_platform_error(self) -> None:
        err = SecureBootParseError("parse failed", text="bad output")
        caught: PlatformError | None = None
        try:
            raise err
        except PlatformError as e:
            caught = e
        assert caught is err

    def test_specific_use_case_unrecognised_state(self) -> None:
        """Simulates the documented error: ``SecureBoot`` has an unrecognised value."""
        err = SecureBootParseError(
            "unrecognised SecureBoot value 'maybe'",
            text="SecureBoot maybe\n",
        )
        assert "unrecognised" in err.message
        assert err.text == "SecureBoot maybe\n"

    def test_specific_use_case_unrecognised_setup_mode(self) -> None:
        """Simulates the documented error: ``SetupMode`` has an unrecognised value."""
        err = SecureBootParseError(
            "unrecognised SetupMode value 'maybe'",
            text="SecureBoot enabled\nSetupMode maybe\n",
        )
        assert "SetupMode" in err.message
        assert err.text == "SecureBoot enabled\nSetupMode maybe\n"
