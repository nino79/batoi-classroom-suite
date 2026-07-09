"""Unit tests for ``bcs.platform.adapters.network.errors``.

Exhaustive coverage of the Network Adapter's error hierarchy:
``NetworkError``, ``NetworkUnavailableError``, and
``NetworkParseError``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from bcs.platform.adapters.network.errors import (
    NetworkError,
    NetworkParseError,
    NetworkUnavailableError,
)
from bcs.platform.errors import PlatformError
from bcs.platform.models import CommandResult


def _make_result(**overrides: Any) -> CommandResult:
    """Return a reproducible ``CommandResult`` for deterministic tests."""
    defaults: dict[str, Any] = {
        "command": ("ip", "-json", "addr", "show"),
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


class TestNetworkError:
    """Tests for the ``NetworkError`` base exception."""

    def test_message_is_stored(self) -> None:
        err = NetworkError("ip exited with code 1")
        assert err.message == "ip exited with code 1"

    def test_message_is_exception_arg(self) -> None:
        err = NetworkError("ip exited with code 1")
        assert str(err) == "ip exited with code 1"

    def test_inherits_from_platform_error(self) -> None:
        assert issubclass(NetworkError, PlatformError)

    def test_result_defaults_to_none(self) -> None:
        err = NetworkError("something went wrong")
        assert err.result is None

    def test_result_can_be_set(self) -> None:
        result = _make_result()
        err = NetworkError("ip failed", result=result)
        assert err.result is result

    def test_result_attribute_is_readable(self) -> None:
        result = _make_result(exit_code=1, stderr="network error")
        err = NetworkError("ip failed", result=result)
        assert err.result is not None
        assert err.result.exit_code == 1
        assert err.result.stderr == "network error"

    def test_can_be_caught_as_platform_error(self) -> None:
        err = NetworkError("ip failed")
        caught: PlatformError | None = None
        try:
            raise err
        except PlatformError as e:
            caught = e
        assert caught is err

    def test_can_be_caught_as_network_error(self) -> None:
        err = NetworkError("ip failed")
        caught: NetworkError | None = None
        try:
            raise err
        except NetworkError as e:
            caught = e
        assert caught is err

    def test_multiple_instances_are_independent(self) -> None:
        err1 = NetworkError("first error")
        err2 = NetworkError("second error")
        assert err1.message != err2.message
        assert err1 is not err2


class TestNetworkUnavailableError:
    """Tests for ``NetworkUnavailableError``."""

    def test_message_is_stored(self) -> None:
        err = NetworkUnavailableError("network data not available")
        assert err.message == "network data not available"

    def test_inherits_from_network_error(self) -> None:
        assert issubclass(NetworkUnavailableError, NetworkError)

    def test_inherits_from_platform_error(self) -> None:
        assert issubclass(NetworkUnavailableError, PlatformError)

    def test_result_defaults_to_none(self) -> None:
        err = NetworkUnavailableError("network data not available")
        assert err.result is None

    def test_result_can_be_set(self) -> None:
        result = _make_result(exit_code=1, stderr="cannot open netlink socket")
        err = NetworkUnavailableError("network data not available", result=result)
        assert err.result is result

    def test_can_be_caught_as_network_error(self) -> None:
        err = NetworkUnavailableError("network data not available")
        caught: NetworkError | None = None
        try:
            raise err
        except NetworkError as e:
            caught = e
        assert caught is err

    def test_can_be_caught_as_platform_error(self) -> None:
        err = NetworkUnavailableError("network data not available")
        caught: PlatformError | None = None
        try:
            raise err
        except PlatformError as e:
            caught = e
        assert caught is err

    def test_specific_use_case_netlink_socket(self) -> None:
        err = NetworkUnavailableError("cannot open netlink socket")
        assert "cannot open" in err.message

    def test_specific_use_case_permission_denied(self) -> None:
        result = _make_result(exit_code=1, stderr="Permission denied")
        err = NetworkUnavailableError(
            "cannot query network interfaces: permission denied", result=result
        )
        assert "permission denied" in err.message
        assert err.result is result

    def test_specific_use_case_network_unreachable(self) -> None:
        err = NetworkUnavailableError("network is unreachable")
        assert "unreachable" in err.message


class TestNetworkParseError:
    """Tests for ``NetworkParseError``."""

    def test_message_is_stored(self) -> None:
        err = NetworkParseError("malformed output", text="not json\n")
        assert err.message == "malformed output"

    def test_inherits_from_network_error(self) -> None:
        assert issubclass(NetworkParseError, NetworkError)

    def test_inherits_from_platform_error(self) -> None:
        assert issubclass(NetworkParseError, PlatformError)

    def test_text_attribute_is_set(self) -> None:
        bad_output = "not json"
        err = NetworkParseError("unparseable output", text=bad_output)
        assert err.text == bad_output

    def test_text_can_be_empty_string(self) -> None:
        err = NetworkParseError("empty output", text="")
        assert err.text == ""

    def test_text_can_be_multiline(self) -> None:
        multiline = "line1\nline2\nline3"
        err = NetworkParseError("not ip-shaped output", text=multiline)
        assert err.text == multiline

    def test_result_defaults_to_none(self) -> None:
        err = NetworkParseError("parse failed", text="bad output")
        assert err.result is None

    def test_can_be_caught_as_network_error(self) -> None:
        err = NetworkParseError("parse failed", text="bad output")
        caught: NetworkError | None = None
        try:
            raise err
        except NetworkError as e:
            caught = e
        assert caught is err

    def test_can_be_caught_as_platform_error(self) -> None:
        err = NetworkParseError("parse failed", text="bad output")
        caught: PlatformError | None = None
        try:
            raise err
        except PlatformError as e:
            caught = e
        assert caught is err

    def test_specific_use_case_invalid_json(self) -> None:
        err = NetworkParseError("output is not valid JSON", text="not json")
        assert "not valid JSON" in err.message
        assert err.text == "not json"

    def test_specific_use_case_malformed_entry(self) -> None:
        err = NetworkParseError(
            "entry 1: missing or empty 'ifname'",
            text='[{"flags": ["UP"]}]',
        )
        assert "ifname" in err.message
        assert err.text == '[{"flags": ["UP"]}]'
