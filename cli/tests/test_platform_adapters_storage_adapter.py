"""Tests for the Storage Adapter orchestration layer.

Follows exactly the same testing philosophy as
``test_platform_adapters_efi_adapter.py``: a ``FakeCommandRunner``
stand-in (not a mock of ``SubprocessCommandRunner``) exercises the
public ``CommandRunner`` interface, simple inline JSON strings stand in
for tool output (the parser's own correctness is covered by
``test_platform_adapters_storage_parser.py`` and is not re-tested
here), and every test asserts zero real subprocess execution ever
occurs - the fake only ever returns/raises exactly what each test
configures it to.

These tests verify that ``read_storage_topology``:
- Invokes ``lsblk``/``blkid``/``findmnt`` in order, with correct
  arguments and locale-forced environment.
- Forwards the timeout parameter identically to all three calls.
- Returns a correctly-parsed ``StorageConfiguration`` on success.
- Propagates ``CommandNotFoundError``/``CommandTimeoutError`` from the
  runner unchanged, from whichever tool raises them.
- Stops calling further tools once one has failed.
- Raises ``StorageUnavailableError`` for a non-zero exit whose stderr
  is recognisably an "environment cannot provide this data" message.
- Raises ``StorageError`` for other non-zero exits.
- Raises ``StorageParseError``, chained from the original
  ``ValueError``, when all three tools succeed but the output cannot
  be parsed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

import pytest

from bcs.platform.adapters.storage.adapter import read_storage_topology
from bcs.platform.adapters.storage.errors import (
    StorageError,
    StorageParseError,
    StorageUnavailableError,
)
from bcs.platform.adapters.storage.models import StorageConfiguration
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
    """A configurable ``CommandRunner`` stand-in, keyed by tool name
    (``command[0]``).

    ``results`` maps a tool name to the canned ``FakeCommandResult``
    returned when it is invoked. ``not_found_tools``/``timeout_tools``
    name tools that raise ``CommandNotFoundError``/``CommandTimeoutError``
    instead. Every call is recorded in ``calls`` regardless of outcome,
    so tests can assert exactly what was (and was not) invoked.
    """

    results: dict[str, FakeCommandResult] = field(default_factory=dict)
    not_found_tools: frozenset[str] = frozenset()
    timeout_tools: frozenset[str] = frozenset()
    calls: list[dict[str, Any]] = field(default_factory=list)

    def run(  # noqa: PLR0913 - mirrors the CommandRunner Protocol's own signature exactly
        self,
        command: Any,
        *,
        timeout_seconds: Any = None,
        check: bool = False,
        cwd: Any = None,
        env: Any = None,
        input_text: Any = None,
    ) -> MagicMock:
        tool = command[0]
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
        # Check not-found / timeout BEFORE touching self.results, so that
        # a FakeCommandRunner configured with only not_found_tools (empty
        # results) correctly raises instead of KeyError-ing on the first
        # tool that *is* in results.
        if tool in self.not_found_tools:
            raise CommandNotFoundError(f"{tool} not found", executable=tool)
        if tool in self.timeout_tools:
            raise CommandTimeoutError(f"{tool} timed out", partial_result=MagicMock())
        return self.results[tool].to_result()


# ---------------------------------------------------------------------------
# Valid output used across tests - minimal, not realistic; parser
# correctness is covered by test_platform_adapters_storage_parser.py.
# ---------------------------------------------------------------------------

_VALID_LSBLK = (
    '{"blockdevices": [{"name": "nvme0n1", "size": 512110190592, "type": "disk", '
    '"ro": false, "rm": false, "mountpoint": null, "children": ['
    '{"name": "nvme0n1p1", "size": 524288000, "mountpoint": "/boot/efi", "partn": 1}'
    "]}]}"
)
_VALID_BLKID = (
    '{"blockdevices": [{"name": "/dev/nvme0n1p1", "type": "vfat", "uuid": "AAAA-BBBB", '
    '"partuuid": "11111111-1111-1111-1111-111111111111", '
    '"parttype": "c12a7328-f81f-11d2-ba4b-00a0c93ec93b"}]}'
)
_VALID_FINDMNT = (
    '{"filesystems": [{"target": "/boot/efi", "source": "/dev/nvme0n1p1", '
    '"fstype": "vfat", "options": "rw,relatime"}]}'
)


def _make_result(*, stdout: str = "", stderr: str = "", exit_code: int = 0) -> FakeCommandResult:
    now = datetime.now(tz=UTC)
    return FakeCommandResult(
        command=("tool",),
        stdout=stdout,
        stderr=stderr,
        exit_code=exit_code,
        duration=0.1,
        started_at=now,
        finished_at=now,
    )


def _successful_runner() -> FakeCommandRunner:
    return FakeCommandRunner(
        results={
            "lsblk": _make_result(stdout=_VALID_LSBLK),
            "blkid": _make_result(stdout=_VALID_BLKID),
            "findmnt": _make_result(stdout=_VALID_FINDMNT),
        }
    )


# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------


def test_calls_correct_commands_in_order_with_locale_env() -> None:
    runner = _successful_runner()
    read_storage_topology(runner)

    assert len(runner.calls) == 3
    lsblk_call, blkid_call, findmnt_call = runner.calls

    assert lsblk_call["command"] == ["lsblk", "-J", "-b"]
    assert blkid_call["command"] == ["blkid", "-p", "-o", "json"]
    assert findmnt_call["command"] == ["findmnt", "-J"]

    for call in runner.calls:
        assert call["check"] is False
        assert call["env"]["LANG"] == "C"
        assert call["env"]["LC_ALL"] == "C"
        assert "PATH" in call["env"]


def test_forwards_timeout_seconds_to_every_call() -> None:
    runner = _successful_runner()
    read_storage_topology(runner, timeout_seconds=25.0)

    assert [call["timeout_seconds"] for call in runner.calls] == [25.0, 25.0, 25.0]


def test_timeout_none_is_forwarded() -> None:
    runner = _successful_runner()
    read_storage_topology(runner, timeout_seconds=None)

    assert all(call["timeout_seconds"] is None for call in runner.calls)


def test_default_timeout_is_ten_seconds() -> None:
    runner = _successful_runner()
    read_storage_topology(runner)

    assert all(call["timeout_seconds"] == 10.0 for call in runner.calls)


def test_returns_parsed_storage_configuration() -> None:
    runner = _successful_runner()
    config = read_storage_topology(runner)

    assert isinstance(config, StorageConfiguration)
    assert len(config.devices) == 1
    disk = config.devices[0]
    assert disk.name == "nvme0n1"
    assert disk.partitions[0].mount_point == "/boot/efi"
    assert disk.partitions[0].filesystem is not None
    assert disk.partitions[0].filesystem.fs_type == "vfat"
    assert len(config.mounts) == 1


# ---------------------------------------------------------------------------
# Platform error propagation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("missing_tool", ["lsblk", "blkid", "findmnt"])
def test_command_not_found_propagates(missing_tool: str) -> None:
    # Tools that run before ``missing_tool`` in the sequence still need a
    # canned successful result to reach it at all.
    runner = _successful_runner()
    runner.not_found_tools = frozenset([missing_tool])

    with pytest.raises(CommandNotFoundError):
        read_storage_topology(runner)


@pytest.mark.parametrize("slow_tool", ["lsblk", "blkid", "findmnt"])
def test_command_timeout_propagates(slow_tool: str) -> None:
    runner = _successful_runner()
    runner.timeout_tools = frozenset([slow_tool])

    with pytest.raises(CommandTimeoutError):
        read_storage_topology(runner)


def test_remaining_tools_are_not_run_after_a_failure() -> None:
    """lsblk fails -> blkid/findmnt must never be invoked."""
    runner = FakeCommandRunner(not_found_tools=frozenset(["lsblk"]))

    with pytest.raises(CommandNotFoundError):
        read_storage_topology(runner)

    assert len(runner.calls) == 1
    assert runner.calls[0]["command"][0] == "lsblk"


# ---------------------------------------------------------------------------
# Non-zero exit: unavailable vs. generic error
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "stderr",
    [
        "Permission denied",
        "lsblk: cannot open /dev/nvme0n1: Operation not permitted",
        "blkid: error: No such file or directory",
        "findmnt: no such device found",
        "No medium found",
        "cannot open device",
        "not authorized to read device",
    ],
)
@pytest.mark.parametrize("failing_tool", ["lsblk", "blkid", "findmnt"])
def test_unavailable_error_for_recognised_stderr_patterns(failing_tool: str, stderr: str) -> None:
    results = {
        "lsblk": _make_result(stdout=_VALID_LSBLK),
        "blkid": _make_result(stdout=_VALID_BLKID),
        "findmnt": _make_result(stdout=_VALID_FINDMNT),
    }
    results[failing_tool] = _make_result(stderr=stderr, exit_code=1)
    runner = FakeCommandRunner(results=results)

    with pytest.raises(StorageUnavailableError) as exc_info:
        read_storage_topology(runner)

    assert exc_info.value.result is not None
    assert exc_info.value.result.exit_code == 1


@pytest.mark.parametrize("failing_tool", ["lsblk", "blkid", "findmnt"])
def test_generic_error_for_unrecognised_stderr(failing_tool: str) -> None:
    results = {
        "lsblk": _make_result(stdout=_VALID_LSBLK),
        "blkid": _make_result(stdout=_VALID_BLKID),
        "findmnt": _make_result(stdout=_VALID_FINDMNT),
    }
    results[failing_tool] = _make_result(stderr="something went wrong", exit_code=2)
    runner = FakeCommandRunner(results=results)

    with pytest.raises(StorageError) as exc_info:
        read_storage_topology(runner)

    assert exc_info.value.result is not None
    assert exc_info.value.result.exit_code == 2
    # Must NOT be the more specific subclass.
    assert not isinstance(exc_info.value, StorageUnavailableError)


# ---------------------------------------------------------------------------
# Parser failure
# ---------------------------------------------------------------------------


def test_parse_error_when_output_is_unrecognisable() -> None:
    runner = FakeCommandRunner(
        results={
            "lsblk": _make_result(stdout="not valid json"),
            "blkid": _make_result(stdout=_VALID_BLKID),
            "findmnt": _make_result(stdout=_VALID_FINDMNT),
        }
    )

    with pytest.raises(StorageParseError) as exc_info:
        read_storage_topology(runner)

    assert "not valid json" in exc_info.value.text
    # Exception chaining is preserved - the original ValueError is
    # reachable via __cause__.
    assert isinstance(exc_info.value.__cause__, ValueError)


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


def test_fake_command_runner_satisfies_protocol() -> None:
    runner = _successful_runner()
    # isinstance check against the runtime-checkable Protocol.
    assert isinstance(runner, CommandRunner)
