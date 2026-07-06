"""The Platform Layer's exception hierarchy.

Design: ``docs/PLATFORM_LAYER.md#exception-hierarchy``, accepted per
``docs/decisions/0009-platform-layer-command-runner.md``.

``PlatformError`` and its subclasses are deliberately **independent**
of ``bcs.errors.BcsError``/``bcs.exit_codes.ExitCode``: those are a
CLI-adapter-level concept (``bcs.__main__.main`` translates a
``BcsError`` into a process exit code), whereas the Platform Layer is
core infrastructure with no knowledge of the CLI's own error/exit-code
scheme - the same core/adapter independence
``docs/decisions/0008-host-inventory-ports-and-adapters.md`` already
established for ``bcs.inventory``. A calling command is free to catch
any exception here and re-raise it as a ``BcsError`` subclass if it
wants a specific process exit code; the Platform Layer itself never
does that translation.

This module defines the exceptions only - no execution logic, no
``subprocess`` usage. They are raised by
:class:`~bcs.platform.execution.SubprocessCommandRunner`.
"""

from __future__ import annotations

from bcs.platform.models import CommandResult


class PlatformError(Exception):
    """Base class for every error the Platform Layer raises intentionally.

    Never raised directly - always one of the subclasses below. Does
    **not** inherit from ``bcs.errors.BcsError``; see this module's
    docstring for why.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class CommandNotFoundError(PlatformError):
    """The executable can't be located or executed at all.

    Translates the underlying ``FileNotFoundError``/``PermissionError``
    ``subprocess`` itself would raise into a Platform Layer-native
    exception, so no caller ever needs to catch a bare ``OSError``.
    """

    def __init__(self, message: str, *, executable: str) -> None:
        super().__init__(message)
        self.executable = executable


class CommandTimeoutError(PlatformError):
    """``timeout_seconds`` elapsed before the process finished.

    Always raised - never returned as a ``CommandResult`` with
    ``timed_out=True`` - per ``docs/PLATFORM_LAYER.md#timeout-handling``'s
    "fail loud" design principle.
    """

    def __init__(self, message: str, *, partial_result: CommandResult) -> None:
        super().__init__(message)
        self.partial_result = partial_result


class CommandExecutionError(PlatformError):
    """``check=True`` was given and the process exited non-zero."""

    def __init__(self, message: str, *, result: CommandResult) -> None:
        super().__init__(message)
        self.result = result


__all__ = [
    "CommandExecutionError",
    "CommandNotFoundError",
    "CommandTimeoutError",
    "PlatformError",
]
