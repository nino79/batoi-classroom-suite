"""Tests for the Network Adapter orchestration layer.

These tests verify that ``read_network_interfaces``:
- Invokes the correct command (``["ip", "-json", "addr", "show"]``)
  with correct locale-forced environment.
- Forwards the timeout parameter correctly, defaulting to 5.0 seconds.
- Returns a correctly-parsed ``NetworkInterfaceStatus`` on success,
  including the empty-array (no interfaces) case.
- Propagates ``CommandNotFoundError`` and ``CommandTimeoutError`` from
  the runner unchanged.
- Raises ``NetworkUnavailableError`` for non-zero exits whose stderr is
  recognisably a "network data unavailable" message.
- Raises ``NetworkError`` for other non-zero exits.
- Raises ``NetworkParseError`` (with ``__cause__`` preserved) when the
  command succeeds but the output cannot be parsed.

A ``FakeCommandRunner`` is used instead of mocking
``SubprocessCommandRunner`` directly, so the tests exercise the public
``CommandRunner`` interface rather than implementation details,
mirroring ``test_platform_adapters_secureboot_adapter.py``'s own style.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

import pytest

from bcs.platform.adapters.network.adapter import read_network_interfaces
from bcs.platform.adapters.network.errors import (
    NetworkError,
    NetworkParseError,
    NetworkUnavailableError,
)
from bcs.platform.adapters.network.models import NetworkInterfaceStatus
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
            raise CommandNotFoundError("ip not found", executable="ip")
        if self.raise_timeout:
            raise CommandTimeoutError(
                "ip timed out",
                partial_result=MagicMock(),
            )
        return self.result.to_result()


_VALID_ETHERNET_UP = (
    '[{"ifname": "eth0", "flags": ["BROADCAST", "MULTICAST", "UP", "LOWER_UP"], '
    '"address": "52:54:00:12:34:56", '
    '"addr_info": [{"family": "inet", "local": "10.0.2.15", "prefixlen": 24}]}]'
)


def _make_result(
    *,
    stdout: str = "",
    stderr: str = "",
    exit_code: int = 0,
) -> FakeCommandResult:
    now = datetime.now(tz=UTC)
    return FakeCommandResult(
        command=("ip", "-json", "addr", "show"),
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
    runner = FakeCommandRunner(result=_make_result(stdout=_VALID_ETHERNET_UP))
    read_network_interfaces(runner)

    assert len(runner.calls) == 1
    call = runner.calls[0]
    assert call["command"] == ["ip", "-json", "addr", "show"]
    assert call["check"] is False
    # Locale must be forced to C for stable output
    assert call["env"]["LANG"] == "C"
    assert call["env"]["LC_ALL"] == "C"
    # PATH and other variables must still be present
    assert "PATH" in call["env"]


def test_default_timeout_is_five_seconds() -> None:
    runner = FakeCommandRunner(result=_make_result(stdout=_VALID_ETHERNET_UP))
    read_network_interfaces(runner)

    assert runner.calls[0]["timeout_seconds"] == 5.0


def test_forwards_timeout_seconds() -> None:
    runner = FakeCommandRunner(result=_make_result(stdout=_VALID_ETHERNET_UP))
    read_network_interfaces(runner, timeout_seconds=15.0)

    assert runner.calls[0]["timeout_seconds"] == 15.0


def test_timeout_none_is_forwarded() -> None:
    runner = FakeCommandRunner(result=_make_result(stdout=_VALID_ETHERNET_UP))
    read_network_interfaces(runner, timeout_seconds=None)

    assert runner.calls[0]["timeout_seconds"] is None


def test_returns_parsed_network_interface_status() -> None:
    runner = FakeCommandRunner(result=_make_result(stdout=_VALID_ETHERNET_UP))
    status = read_network_interfaces(runner)

    assert isinstance(status, NetworkInterfaceStatus)
    assert len(status.interfaces) == 1
    assert status.interfaces[0].name == "eth0"
    assert status.interfaces[0].mac_address == "52:54:00:12:34:56"
    assert status.interfaces[0].ip_addresses == ("10.0.2.15",)
    assert status.interfaces[0].is_up is True
    assert status.raw_text == _VALID_ETHERNET_UP


def test_empty_json_array_is_a_valid_non_error_result() -> None:
    """A zero-exit, empty-array result is a normal, valid outcome - not
    an error - per docs/NETWORK_ADAPTER.md#parser-strategy.
    """
    runner = FakeCommandRunner(result=_make_result(stdout="[]"))
    status = read_network_interfaces(runner)

    assert status.interfaces == ()


# ---------------------------------------------------------------------------
# Platform error propagation
# ---------------------------------------------------------------------------


def test_command_not_found_propagates() -> None:
    runner = FakeCommandRunner(raise_not_found=True)

    with pytest.raises(CommandNotFoundError):
        read_network_interfaces(runner)


def test_command_timeout_propagates() -> None:
    runner = FakeCommandRunner(raise_timeout=True)

    with pytest.raises(CommandTimeoutError):
        read_network_interfaces(runner)


# ---------------------------------------------------------------------------
# Non-zero exit: unavailable vs. generic error
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "stderr",
    [
        "Error: ip: network namespace not accessible.",
        "Cannot open netlink socket: Protocol not supported",
        "ip: Permission denied",
        "RTNETLINK answers: Network is unreachable",
    ],
)
def test_unavailable_error_for_recognised_stderr_patterns(stderr: str) -> None:
    runner = FakeCommandRunner(result=_make_result(stderr=stderr, exit_code=1))

    with pytest.raises(NetworkUnavailableError) as exc_info:
        read_network_interfaces(runner)

    assert exc_info.value.result is not None
    assert exc_info.value.result.exit_code == 1


def test_generic_error_for_unrecognised_stderr() -> None:
    runner = FakeCommandRunner(result=_make_result(stderr="something went wrong", exit_code=1))

    with pytest.raises(NetworkError) as exc_info:
        read_network_interfaces(runner)

    assert exc_info.value.result is not None
    assert exc_info.value.result.exit_code == 1
    # Must NOT be the more specific subclass
    assert not isinstance(exc_info.value, NetworkUnavailableError)


# ---------------------------------------------------------------------------
# Parser failure
# ---------------------------------------------------------------------------


def test_parse_error_for_invalid_json() -> None:
    runner = FakeCommandRunner(result=_make_result(stdout="not json"))

    with pytest.raises(NetworkParseError) as exc_info:
        read_network_interfaces(runner)

    assert exc_info.value.text == "not json"


def test_parse_error_preserves_cause() -> None:
    runner = FakeCommandRunner(result=_make_result(stdout="not json"))

    with pytest.raises(NetworkParseError) as exc_info:
        read_network_interfaces(runner)

    assert exc_info.value.__cause__ is not None
    assert isinstance(exc_info.value.__cause__, ValueError)


def test_parse_error_for_malformed_entry() -> None:
    runner = FakeCommandRunner(result=_make_result(stdout='[{"flags": ["UP", "LOWER_UP"]}]'))

    with pytest.raises(NetworkParseError):
        read_network_interfaces(runner)


def test_parse_error_for_non_array_top_level() -> None:
    runner = FakeCommandRunner(result=_make_result(stdout='{"ifname": "eth0"}'))

    with pytest.raises(NetworkParseError):
        read_network_interfaces(runner)


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


def test_fake_command_runner_satisfies_protocol() -> None:
    runner = FakeCommandRunner(result=_make_result(stdout=_VALID_ETHERNET_UP))
    # isinstance check against the runtime-checkable Protocol
    assert isinstance(runner, CommandRunner)
