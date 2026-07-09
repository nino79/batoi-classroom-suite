"""Tests for the Filesystem Adapter orchestration layer.

These tests verify that ``read_filesystem_usage``:
- Invokes the correct command (including ``-a``) with correct
  locale-forced environment.
- Forwards the timeout parameter correctly, defaulting to 10.0 seconds.
- Returns a correctly-parsed ``FilesystemUsageReport`` on success, with
  ``raw_stderr`` attached from the real ``CommandResult.stderr``.
- On a non-zero exit that still yields at least one parsed filesystem,
  returns that data normally (not raised as an error) with the real
  ``stderr`` attached to ``raw_stderr`` - the partial-failure case
  unique to this adapter.
- Propagates ``CommandNotFoundError`` and ``CommandTimeoutError`` from
  the runner unchanged.
- Raises ``FilesystemUnavailableError`` for a non-zero exit with zero
  parsed entries whose stderr is recognisably a "filesystem data
  unavailable" message.
- Raises ``FilesystemError`` for other non-zero exits with zero parsed
  entries.
- Raises ``FilesystemParseError`` when the command succeeds (zero
  exit) but zero entries could be parsed, or when the parser raises a
  malformed-row/field ``ValueError``.

A ``FakeCommandRunner`` is used instead of mocking
``SubprocessCommandRunner`` directly, so the tests exercise the public
``CommandRunner`` interface rather than implementation details,
mirroring ``test_platform_adapters_secureboot_adapter.py``'s own style.
"""

from __future__ import annotations

import pytest
from tests.fake_command_runner import FakeCommandRunner, build_command_result

from bcs.platform.adapters.filesystem.adapter import read_filesystem_usage
from bcs.platform.adapters.filesystem.errors import (
    FilesystemError,
    FilesystemParseError,
    FilesystemUnavailableError,
)
from bcs.platform.adapters.filesystem.models import FilesystemUsageReport
from bcs.platform.errors import CommandNotFoundError, CommandTimeoutError
from bcs.platform.execution import CommandRunner

_ONE_FILESYSTEM = (
    "/dev/nvme0n1p2 ext4 32768000 512000 32256000 512110190592 128027547648 358486736896 /\n"
)
_TWO_FILESYSTEMS = (
    _ONE_FILESYSTEM + "/dev/nvme0n1p1 vfat - - - 524288000 104857600 419430400 /boot/efi\n"
)


# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------


def _df_result(**kw: str | int) -> FakeCommandRunner:
    return FakeCommandRunner(
        result=build_command_result(command=("df",), **kw)  # type: ignore[arg-type]
    )


def test_calls_correct_command_with_locale_env() -> None:
    runner = _df_result(stdout=_ONE_FILESYSTEM)
    read_filesystem_usage(runner)

    assert len(runner.calls) == 1
    call = runner.calls[0]
    assert call["command"] == [
        "df",
        "--output=source,fstype,itotal,iused,iavail,size,used,avail,target",
        "-B1",
        "-a",
    ]
    assert call["check"] is False
    assert call["env"]["LANG"] == "C"
    assert call["env"]["LC_ALL"] == "C"
    assert "PATH" in call["env"]


def test_default_timeout_is_ten_seconds() -> None:
    runner = _df_result(stdout=_ONE_FILESYSTEM)
    read_filesystem_usage(runner)

    assert runner.calls[0]["timeout_seconds"] == 10.0


def test_forwards_timeout_seconds() -> None:
    runner = _df_result(stdout=_ONE_FILESYSTEM)
    read_filesystem_usage(runner, timeout_seconds=30.0)

    assert runner.calls[0]["timeout_seconds"] == 30.0


def test_timeout_none_is_forwarded() -> None:
    runner = _df_result(stdout=_ONE_FILESYSTEM)
    read_filesystem_usage(runner, timeout_seconds=None)

    assert runner.calls[0]["timeout_seconds"] is None


def test_returns_parsed_report_with_multiple_filesystems() -> None:
    runner = _df_result(stdout=_TWO_FILESYSTEMS)
    report = read_filesystem_usage(runner)

    assert isinstance(report, FilesystemUsageReport)
    assert len(report.filesystems) == 2
    assert report.filesystems[0].target == "/"
    assert report.filesystems[1].target == "/boot/efi"


def test_zero_exit_clean_result_has_empty_raw_stderr() -> None:
    runner = _df_result(stdout=_ONE_FILESYSTEM, stderr="")
    report = read_filesystem_usage(runner)

    assert report.raw_stderr == ""


# ---------------------------------------------------------------------------
# The unique judgment call: partial failure, data still returned
# ---------------------------------------------------------------------------


def test_non_zero_exit_with_at_least_one_parsed_entry_is_not_raised() -> None:
    """A stale mount causing df to exit non-zero must not discard every
    other filesystem it could still read - see
    docs/FILESYSTEM_ADAPTER.md#adapter-responsibilities point 4.
    """
    runner = _df_result(
        stdout=_ONE_FILESYSTEM,
        stderr="df: '/mnt/stale': Stale file handle",
        exit_code=1,
    )
    report = read_filesystem_usage(runner)

    assert len(report.filesystems) == 1
    assert report.raw_stderr == "df: '/mnt/stale': Stale file handle"


def test_partial_failure_raw_stderr_is_attached_verbatim() -> None:
    runner = _df_result(
        stdout=_TWO_FILESYSTEMS,
        stderr="df: '/mnt/stale': Stale file handle",
        exit_code=1,
    )
    report = read_filesystem_usage(runner)

    assert len(report.filesystems) == 2
    assert report.raw_stderr == "df: '/mnt/stale': Stale file handle"


# ---------------------------------------------------------------------------
# Platform error propagation
# ---------------------------------------------------------------------------


def test_command_not_found_propagates() -> None:
    runner = FakeCommandRunner(not_found_tools=frozenset({"df"}))

    with pytest.raises(CommandNotFoundError):
        read_filesystem_usage(runner)


def test_command_timeout_propagates() -> None:
    runner = FakeCommandRunner(timeout_tools=frozenset({"df"}))

    with pytest.raises(CommandTimeoutError):
        read_filesystem_usage(runner)


# ---------------------------------------------------------------------------
# Non-zero exit, zero parsed entries: unavailable vs. generic error
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "stderr",
    [
        "df: Permission denied",
        "df: Operation not permitted",
        "df: no file systems processed",
        "df: cannot read table of mounted file systems",
    ],
)
def test_unavailable_error_for_recognised_stderr_patterns_with_zero_entries(
    stderr: str,
) -> None:
    runner = _df_result(stdout="", stderr=stderr, exit_code=1)

    with pytest.raises(FilesystemUnavailableError) as exc_info:
        read_filesystem_usage(runner)

    assert exc_info.value.result is not None
    assert exc_info.value.result.exit_code == 1


def test_generic_error_for_unrecognised_stderr_with_zero_entries() -> None:
    runner = _df_result(stdout="", stderr="something went wrong", exit_code=1)

    with pytest.raises(FilesystemError) as exc_info:
        read_filesystem_usage(runner)

    assert exc_info.value.result is not None
    assert exc_info.value.result.exit_code == 1
    assert not isinstance(exc_info.value, FilesystemUnavailableError)


def test_header_only_stdout_with_non_zero_exit_and_unrecognised_stderr_is_generic_error() -> None:
    """Zero data rows parsed (only a header) plus a non-zero exit with
    no recognisable 'unavailable' pattern - the base FilesystemError,
    not FilesystemParseError, per docs/FILESYSTEM_ADAPTER.md#error-mapping.
    """
    header = "Filesystem Type Inodes IUsed IFree 1B-blocks Used Available Mounted on\n"
    runner = _df_result(stdout=header, stderr="unexpected failure", exit_code=1)

    with pytest.raises(FilesystemError) as exc_info:
        read_filesystem_usage(runner)
    assert not isinstance(exc_info.value, FilesystemUnavailableError | FilesystemParseError)


# ---------------------------------------------------------------------------
# Parser failure / zero-exit zero-entries
# ---------------------------------------------------------------------------


def test_parse_error_for_malformed_row() -> None:
    runner = _df_result(stdout="/dev/nvme0n1p2 ext4 32768000\n")

    with pytest.raises(FilesystemParseError) as exc_info:
        read_filesystem_usage(runner)

    assert "malformed row" in str(exc_info.value)
    assert exc_info.value.text == "/dev/nvme0n1p2 ext4 32768000\n"


def test_parse_error_for_malformed_field() -> None:
    bad_line = "/dev/nvme0n1p2 ext4 32768000 512000 32256000 abc 128027547648 358486736896 /\n"
    runner = _df_result(stdout=bad_line)

    with pytest.raises(FilesystemParseError) as exc_info:
        read_filesystem_usage(runner)

    assert "malformed size" in str(exc_info.value)
    assert exc_info.value.text == bad_line


def test_zero_exit_with_zero_parsed_entries_is_parse_error() -> None:
    """A real, if unusual, empty machine state and 'not df-shaped output
    at all' are both mapped to FilesystemParseError here - a narrow,
    accepted ambiguity, per docs/FILESYSTEM_ADAPTER.md#open-questions.
    """
    header = "Filesystem Type Inodes IUsed IFree 1B-blocks Used Available Mounted on\n"
    runner = _df_result(stdout=header, exit_code=0)

    with pytest.raises(FilesystemParseError) as exc_info:
        read_filesystem_usage(runner)
    assert exc_info.value.text == header


def test_zero_exit_empty_stdout_is_parse_error() -> None:
    runner = _df_result(stdout="", exit_code=0)

    with pytest.raises(FilesystemParseError):
        read_filesystem_usage(runner)


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


def test_fake_command_runner_satisfies_protocol() -> None:
    runner = _df_result(stdout=_ONE_FILESYSTEM)
    assert isinstance(runner, CommandRunner)
