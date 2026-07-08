"""Unit tests for ``bcs.platform.adapters.filesystem.errors``.

Exhaustive coverage of the Filesystem Adapter's error hierarchy:
``FilesystemError``, ``FilesystemUnavailableError``, and
``FilesystemParseError``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from bcs.platform.adapters.filesystem.errors import (
    FilesystemError,
    FilesystemParseError,
    FilesystemUnavailableError,
)
from bcs.platform.errors import PlatformError
from bcs.platform.models import CommandResult

# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


def _make_result(**overrides: Any) -> CommandResult:
    """Return a reproducible ``CommandResult`` for deterministic tests."""
    defaults: dict[str, Any] = {
        "command": ("df", "--output=source,fstype,itotal,iused,iavail,size,used,avail,target"),
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
# FilesystemError
# ---------------------------------------------------------------------------


class TestFilesystemError:
    """Tests for the ``FilesystemError`` base exception."""

    def test_message_is_stored(self) -> None:
        err = FilesystemError("df exited with code 2")
        assert err.message == "df exited with code 2"

    def test_message_is_exception_arg(self) -> None:
        err = FilesystemError("df exited with code 2")
        assert str(err) == "df exited with code 2"

    def test_inherits_from_platform_error(self) -> None:
        assert issubclass(FilesystemError, PlatformError)

    def test_result_defaults_to_none(self) -> None:
        err = FilesystemError("something went wrong")
        assert err.result is None

    def test_result_can_be_set(self) -> None:
        result = _make_result()
        err = FilesystemError("df failed", result=result)
        assert err.result is result

    def test_result_attribute_is_readable(self) -> None:
        result = _make_result(exit_code=1, stderr="df: cannot process")
        err = FilesystemError("df failed", result=result)
        assert err.result is not None
        assert err.result.exit_code == 1
        assert err.result.stderr == "df: cannot process"

    def test_can_be_caught_as_platform_error(self) -> None:
        err = FilesystemError("df failed")
        caught: PlatformError | None = None
        try:
            raise err
        except PlatformError as e:
            caught = e
        assert caught is err

    def test_can_be_caught_as_filesystem_error(self) -> None:
        err = FilesystemError("df failed")
        caught: FilesystemError | None = None
        try:
            raise err
        except FilesystemError as e:
            caught = e
        assert caught is err

    def test_multiple_instances_are_independent(self) -> None:
        err1 = FilesystemError("first error")
        err2 = FilesystemError("second error")
        assert err1.message != err2.message
        assert err1 is not err2


# ---------------------------------------------------------------------------
# FilesystemUnavailableError
# ---------------------------------------------------------------------------


class TestFilesystemUnavailableError:
    """Tests for ``FilesystemUnavailableError``."""

    def test_message_is_stored(self) -> None:
        err = FilesystemUnavailableError("df not found")
        assert err.message == "df not found"

    def test_inherits_from_filesystem_error(self) -> None:
        assert issubclass(FilesystemUnavailableError, FilesystemError)

    def test_inherits_from_platform_error(self) -> None:
        assert issubclass(FilesystemUnavailableError, PlatformError)

    def test_result_defaults_to_none(self) -> None:
        err = FilesystemUnavailableError("df not found")
        assert err.result is None

    def test_result_can_be_set(self) -> None:
        result = _make_result(exit_code=127, stderr="command not found")
        err = FilesystemUnavailableError("df not found", result=result)
        assert err.result is result

    def test_can_be_caught_as_filesystem_error(self) -> None:
        err = FilesystemUnavailableError("df not found")
        caught: FilesystemError | None = None
        try:
            raise err
        except FilesystemError as e:
            caught = e
        assert caught is err

    def test_can_be_caught_as_platform_error(self) -> None:
        err = FilesystemUnavailableError("df not found")
        caught: PlatformError | None = None
        try:
            raise err
        except PlatformError as e:
            caught = e
        assert caught is err

    def test_specific_use_case_permission_denied(self) -> None:
        """Simulates the documented error: permission denied reading mounts."""
        result = _make_result(exit_code=1, stderr="df: Permission denied")
        err = FilesystemUnavailableError(
            "cannot enumerate filesystems: permission denied", result=result
        )
        assert "permission denied" in err.message
        assert err.result is result

    def test_specific_use_case_no_filesystems_processed(self) -> None:
        """Simulates the documented error: nothing mounted in a restricted namespace."""
        result = _make_result(exit_code=1, stderr="df: no file systems processed")
        err = FilesystemUnavailableError(
            "filesystem usage data is not available in this environment", result=result
        )
        assert "not available" in err.message
        assert err.result is result

    def test_partial_failure_is_not_this_exception(self) -> None:
        """This exception is reserved for zero-entries-parsed failures - a
        partial df failure (at least one filesystem still read) is
        returned normally with raw_stderr attached, never raised as
        this - see docs/FILESYSTEM_ADAPTER.md#adapter-responsibilities.
        This test documents that distinction; it does not exercise the
        adapter itself (see test_platform_adapters_filesystem_adapter.py).
        """
        err = FilesystemUnavailableError("no filesystems could be read at all")
        assert "no filesystems" in err.message


# ---------------------------------------------------------------------------
# FilesystemParseError
# ---------------------------------------------------------------------------


class TestFilesystemParseError:
    """Tests for ``FilesystemParseError``."""

    def test_message_is_stored(self) -> None:
        err = FilesystemParseError("malformed output", text="garbage\n")
        assert err.message == "malformed output"

    def test_inherits_from_filesystem_error(self) -> None:
        assert issubclass(FilesystemParseError, FilesystemError)

    def test_inherits_from_platform_error(self) -> None:
        assert issubclass(FilesystemParseError, PlatformError)

    def test_text_attribute_is_set(self) -> None:
        bad_output = "not df-shaped output\n"
        err = FilesystemParseError("unrecognised output", text=bad_output)
        assert err.text == bad_output

    def test_text_can_be_empty_string(self) -> None:
        err = FilesystemParseError("empty output", text="")
        assert err.text == ""

    def test_text_can_be_multiline(self) -> None:
        multiline = "line1\nline2\nline3"
        err = FilesystemParseError("not df-shaped output", text=multiline)
        assert err.text == multiline

    def test_result_defaults_to_none(self) -> None:
        err = FilesystemParseError("parse failed", text="not df output")
        assert err.result is None

    def test_can_be_caught_as_filesystem_error(self) -> None:
        err = FilesystemParseError("parse failed", text="bad output")
        caught: FilesystemError | None = None
        try:
            raise err
        except FilesystemError as e:
            caught = e
        assert caught is err

    def test_can_be_caught_as_platform_error(self) -> None:
        err = FilesystemParseError("parse failed", text="bad output")
        caught: PlatformError | None = None
        try:
            raise err
        except PlatformError as e:
            caught = e
        assert caught is err

    def test_specific_use_case_malformed_row(self) -> None:
        """Simulates the documented error: a row with too few fields."""
        bad_output = "/dev/nvme0n1p2 ext4 32768000\n"
        err = FilesystemParseError(
            f"Failed to parse df output: malformed row (line 1): {bad_output!r}",
            text=bad_output,
        )
        assert "malformed row" in err.message
        assert err.text == bad_output

    def test_specific_use_case_no_recognizable_data(self) -> None:
        """Simulates the documented error: a zero-exit result with zero
        parseable filesystem entries - a real, if unusual, empty
        machine state, per docs/FILESYSTEM_ADAPTER.md#error-mapping.
        """
        err = FilesystemParseError(
            "df output contained no recognizable filesystem usage data.",
            text="",
        )
        assert "no recognizable filesystem usage data" in err.message
        assert err.text == ""
