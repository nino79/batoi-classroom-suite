"""Exit code scheme shared by every ``bcs`` command.

This is the executable form of the table in ``docs/CLI.md#exit-codes``
(``CLI-004``). Every command maps its outcomes onto these values; no
command defines a bespoke code of its own.
"""

from __future__ import annotations

from enum import IntEnum


class ExitCode(IntEnum):
    """Exit codes for the ``bcs`` process, per ``docs/CLI.md#exit-codes``."""

    SUCCESS = 0
    GENERAL_ERROR = 1
    USAGE_ERROR = 2
    CONFIG_INVALID = 3
    PRECONDITION_FAILED = 4
    ABORTED = 5
    PARTIAL_FAILURE = 6
    TIMEOUT = 7
    PLUGIN_ERROR = 8
    INTERRUPTED = 130
    TERMINATED = 143
