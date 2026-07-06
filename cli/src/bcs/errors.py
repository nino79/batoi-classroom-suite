"""The ``bcs`` error hierarchy.

Every error a command raises carries the :class:`~bcs.exit_codes.ExitCode`
it must produce, so the top-level entry point (``bcs.__main__.main``) can
translate *any* ``BcsError`` into the correct process exit code and a
clean, single-line message on stderr, per ``docs/CLI.md``'s "stdout is
data, stderr is everything else" rule (``CLI-005``).
"""

from __future__ import annotations

from bcs.exit_codes import ExitCode


class BcsError(Exception):
    """Base class for every error ``bcs`` raises intentionally.

    Anything that is *not* a ``BcsError`` reaching the entry point is, by
    definition, an unexpected failure and is reported as
    :attr:`~bcs.exit_codes.ExitCode.GENERAL_ERROR`.
    """

    exit_code: ExitCode = ExitCode.GENERAL_ERROR

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class UsageError(BcsError):
    """Bad flags/arguments/unknown command - ``ExitCode.USAGE_ERROR``."""

    exit_code = ExitCode.USAGE_ERROR


class ConfigInvalidError(BcsError):
    """A ClassroomConfig document failed to load or validate.

    Covers YAML syntax errors, an unrecognized ``apiVersion``/``kind``,
    schema violations, and failed semantic checks alike - see
    ``docs/CLI.md``'s rule for exit code ``2`` vs. ``3``.
    """

    exit_code = ExitCode.CONFIG_INVALID

    def __init__(self, message: str, *, errors: list[str] | None = None) -> None:
        super().__init__(message)
        self.errors = errors or []


class PreconditionFailedError(BcsError):
    """An environment/platform prerequisite is not met."""

    exit_code = ExitCode.PRECONDITION_FAILED


class AbortedError(BcsError):
    """A confirmation prompt was declined, or required but unanswerable.

    The latter case is ``--no-input`` set without ``--yes`` on a
    destructive command - see ``docs/CLI.md#security-considerations``:
    "non-interactive is not the same as consenting."
    """

    exit_code = ExitCode.ABORTED


class PartialFailureError(BcsError):
    """A multi-target operation where some, but not all, targets failed."""

    exit_code = ExitCode.PARTIAL_FAILURE


class BcsTimeoutError(BcsError):
    """A ``--timeout`` (or command-specific) budget elapsed."""

    exit_code = ExitCode.TIMEOUT


class PluginError(BcsError):
    """An external ``bcs-<name>`` command could not be found or run."""

    exit_code = ExitCode.PLUGIN_ERROR
