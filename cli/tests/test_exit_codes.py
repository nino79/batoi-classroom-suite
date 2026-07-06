from __future__ import annotations

from bcs.exit_codes import ExitCode


def test_values_match_docs_cli_md() -> None:
    """Locks the exit code scheme to docs/CLI.md#exit-codes exactly."""
    assert ExitCode.SUCCESS == 0
    assert ExitCode.GENERAL_ERROR == 1
    assert ExitCode.USAGE_ERROR == 2
    assert ExitCode.CONFIG_INVALID == 3
    assert ExitCode.PRECONDITION_FAILED == 4
    assert ExitCode.ABORTED == 5
    assert ExitCode.PARTIAL_FAILURE == 6
    assert ExitCode.TIMEOUT == 7
    assert ExitCode.PLUGIN_ERROR == 8
    assert ExitCode.INTERRUPTED == 130
    assert ExitCode.TERMINATED == 143


def test_is_int_enum() -> None:
    assert int(ExitCode.CONFIG_INVALID) == 3
