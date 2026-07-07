"""Unit tests for ``bcs.platform.adapters.storage.errors``.

Exhaustive coverage of the Storage Adapter's error hierarchy:
``StorageError``, ``StorageUnavailableError``, and ``StorageParseError``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from bcs.platform.adapters.storage.errors import (
    StorageError,
    StorageParseError,
    StorageUnavailableError,
)
from bcs.platform.errors import PlatformError
from bcs.platform.models import CommandResult

# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


def _make_result(**overrides: Any) -> CommandResult:
    """Return a reproducible ``CommandResult`` for deterministic tests."""
    defaults: dict[str, Any] = {
        "command": ("lsblk", "-J", "-b"),
        "stdout": '{"blockdevices": []}',
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
# StorageError
# ---------------------------------------------------------------------------


class TestStorageError:
    """Tests for the ``StorageError`` base exception."""

    def test_message_is_stored(self) -> None:
        err = StorageError("lsblk exited with code 2")
        assert err.message == "lsblk exited with code 2"

    def test_message_is_exception_arg(self) -> None:
        err = StorageError("lsblk exited with code 2")
        assert str(err) == "lsblk exited with code 2"

    def test_inherits_from_platform_error(self) -> None:
        assert issubclass(StorageError, PlatformError)

    def test_result_defaults_to_none(self) -> None:
        err = StorageError("something went wrong")
        assert err.result is None

    def test_result_can_be_set(self) -> None:
        result = _make_result()
        err = StorageError("lsblk failed", result=result)
        assert err.result is result

    def test_result_attribute_is_readable(self) -> None:
        result = _make_result(exit_code=1, stderr="permission denied")
        err = StorageError("lsblk failed", result=result)
        assert err.result is not None
        assert err.result.exit_code == 1
        assert err.result.stderr == "permission denied"

    def test_can_be_caught_as_platform_error(self) -> None:
        err = StorageError("lsblk failed")
        caught: PlatformError | None = None
        try:
            raise err
        except PlatformError as e:
            caught = e
        assert caught is err

    def test_can_be_caught_as_storage_error(self) -> None:
        err = StorageError("blkid failed")
        caught: StorageError | None = None
        try:
            raise err
        except StorageError as e:
            caught = e
        assert caught is err

    def test_multiple_instances_are_independent(self) -> None:
        err1 = StorageError("first error")
        err2 = StorageError("second error")
        assert err1.message != err2.message
        assert err1 is not err2


# ---------------------------------------------------------------------------
# StorageUnavailableError
# ---------------------------------------------------------------------------


class TestStorageUnavailableError:
    """Tests for ``StorageUnavailableError``."""

    def test_message_is_stored(self) -> None:
        err = StorageUnavailableError("lsblk not found")
        assert err.message == "lsblk not found"

    def test_inherits_from_storage_error(self) -> None:
        assert issubclass(StorageUnavailableError, StorageError)

    def test_inherits_from_platform_error(self) -> None:
        assert issubclass(StorageUnavailableError, PlatformError)

    def test_result_defaults_to_none(self) -> None:
        err = StorageUnavailableError("blkid not found")
        assert err.result is None

    def test_result_can_be_set(self) -> None:
        result = _make_result(exit_code=127, stderr="command not found")
        err = StorageUnavailableError("blkid not found", result=result)
        assert err.result is result

    def test_can_be_caught_as_storage_error(self) -> None:
        err = StorageUnavailableError("findmnt not found")
        caught: StorageError | None = None
        try:
            raise err
        except StorageError as e:
            caught = e
        assert caught is err

    def test_can_be_caught_as_platform_error(self) -> None:
        err = StorageUnavailableError("lsblk not found")
        caught: PlatformError | None = None
        try:
            raise err
        except PlatformError as e:
            caught = e
        assert caught is err

    def test_specific_use_case_tool_not_found(self) -> None:
        """Simulates the documented error: ``lsblk`` not found."""
        err = StorageUnavailableError("lsblk not found")
        assert "lsblk" in err.message
        assert "not found" in err.message

    def test_specific_use_case_permission_denied(self) -> None:
        """Simulates the documented error: permission denied accessing device."""
        result = _make_result(exit_code=1, stderr="permission denied")
        err = StorageUnavailableError("cannot read /dev/sda: permission denied", result=result)
        assert "permission denied" in err.message
        assert err.result is result

    def test_specific_use_case_device_missing(self) -> None:
        """Simulates the documented error: device path does not exist."""
        err = StorageUnavailableError("/dev/sdz not found")
        assert "/dev/sdz" in err.message


# ---------------------------------------------------------------------------
# StorageParseError
# ---------------------------------------------------------------------------


class TestStorageParseError:
    """Tests for ``StorageParseError``."""

    def test_message_is_stored(self) -> None:
        err = StorageParseError("malformed JSON", text='{"blockdevices":')
        assert err.message == "malformed JSON"

    def test_inherits_from_storage_error(self) -> None:
        assert issubclass(StorageParseError, StorageError)

    def test_inherits_from_platform_error(self) -> None:
        assert issubclass(StorageParseError, PlatformError)

    def test_text_attribute_is_set(self) -> None:
        bad_output = '{"blockdevices": [}'
        err = StorageParseError("unexpected end of JSON", text=bad_output)
        assert err.text == bad_output

    def test_text_can_be_empty_string(self) -> None:
        err = StorageParseError("empty output", text="")
        assert err.text == ""

    def test_text_can_be_multiline(self) -> None:
        multiline = "line1\nline2\nline3"
        err = StorageParseError("not JSON", text=multiline)
        assert err.text == multiline

    def test_result_defaults_to_none(self) -> None:
        err = StorageParseError("parse failed", text="not json")
        assert err.result is None

    def test_can_be_caught_as_storage_error(self) -> None:
        err = StorageParseError("malformed", text="{}")
        caught: StorageError | None = None
        try:
            raise err
        except StorageError as e:
            caught = e
        assert caught is err

    def test_can_be_caught_as_platform_error(self) -> None:
        err = StorageParseError("malformed", text="{}")
        caught: PlatformError | None = None
        try:
            raise err
        except PlatformError as e:
            caught = e
        assert caught is err

    def test_specific_use_case_malformed_json(self) -> None:
        """Simulates the documented error: JSON structure is malformed."""
        bad_json = '{"blockdevices": [ incomplete'
        err = StorageParseError("lsblk output is not valid JSON", text=bad_json)
        assert "not valid JSON" in err.message
        assert err.text == bad_json

    def test_specific_use_case_unexpected_structure(self) -> None:
        """Simulates the documented error: output doesn't match expected schema."""
        unexpected = '{"devices": []}'  # wrong key name
        err = StorageParseError("lsblk output missing 'blockdevices' key", text=unexpected)
        assert "missing 'blockdevices'" in err.message
        assert err.text == unexpected

    def test_specific_use_case_empty_output(self) -> None:
        """Simulates the documented error: command succeeded but returned nothing."""
        err = StorageParseError("blkid returned empty output", text="")
        assert "empty output" in err.message
        assert err.text == ""

    def test_text_attribute_is_accessible_after_raise(self) -> None:
        bad_output = '{"blockdevices": null}'
        err = StorageParseError("unexpected null", text=bad_output)
        try:
            raise err
        except StorageParseError as caught:
            assert caught.text == bad_output


# ---------------------------------------------------------------------------
# Cross-class hierarchy tests
# ---------------------------------------------------------------------------


class TestHierarchy:
    """Verify the complete exception hierarchy."""

    def test_storage_error_is_platform_error(self) -> None:
        assert issubclass(StorageError, PlatformError)

    def test_storage_unavailable_error_is_storage_error(self) -> None:
        assert issubclass(StorageUnavailableError, StorageError)

    def test_storage_parse_error_is_storage_error(self) -> None:
        assert issubclass(StorageParseError, StorageError)

    def test_storage_unavailable_error_is_platform_error(self) -> None:
        assert issubclass(StorageUnavailableError, PlatformError)

    def test_storage_parse_error_is_platform_error(self) -> None:
        assert issubclass(StorageParseError, PlatformError)

    def test_catch_platform_error_catches_all(self) -> None:
        """Catching PlatformError must catch every storage error."""
        errors: list[Exception] = [
            StorageError("base"),
            StorageUnavailableError("unavailable"),
            StorageParseError("parse", text=""),
        ]
        for err in errors:
            caught: PlatformError | None = None
            try:
                raise err
            except PlatformError as e:
                caught = e
            assert caught is err

    def test_catch_storage_error_catches_subclasses(self) -> None:
        """Catching StorageError must catch both subclasses."""
        errors: list[Exception] = [
            StorageUnavailableError("unavailable"),
            StorageParseError("parse", text=""),
        ]
        for err in errors:
            caught: StorageError | None = None
            try:
                raise err
            except StorageError as e:
                caught = e
            assert caught is err

    def test_catch_storage_unavailable_does_not_catch_parse(self) -> None:
        """Catching StorageUnavailableError must NOT catch StorageParseError."""
        err = StorageParseError("parse error", text="bad")
        caught = False
        try:
            raise err
        except StorageUnavailableError:
            caught = True
        except StorageParseError:
            caught = False  # Expected: caught by the more specific type
        assert caught is False

    def test_catch_storage_parse_does_not_catch_unavailable(self) -> None:
        """Catching StorageParseError must NOT catch StorageUnavailableError."""
        err = StorageUnavailableError("unavailable")
        caught = False
        try:
            raise err
        except StorageParseError:
            caught = True
        except StorageUnavailableError:
            caught = False  # Expected: caught by the more specific type
        assert caught is False


# ---------------------------------------------------------------------------
# Module __all__ contract
# ---------------------------------------------------------------------------


class TestModuleExports:
    """Verify ``__all__`` contains exactly the expected symbols."""

    def test_all_contains_expected_symbols(self) -> None:
        from bcs.platform.adapters.storage import errors

        assert "StorageError" in errors.__all__
        assert "StorageParseError" in errors.__all__
        assert "StorageUnavailableError" in errors.__all__
        assert len(errors.__all__) == 3

    def test_all_symbols_are_importable(self) -> None:
        # These are already imported at the top of this file, but verify:
        from bcs.platform.adapters.storage.errors import (
            StorageError,
            StorageParseError,
            StorageUnavailableError,
        )

        assert StorageError is not None
        assert StorageParseError is not None
        assert StorageUnavailableError is not None
