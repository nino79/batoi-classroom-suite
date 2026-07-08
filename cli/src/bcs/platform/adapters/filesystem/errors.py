"""Domain-specific exceptions for the Filesystem Adapter.

These exceptions extend the Platform Layer's existing hierarchy so that
a caller can ``except bcs.platform.errors.PlatformError`` once and catch
every Platform Layer failure (core or adapter) uniformly.

Naming follows the domain-driven naming rule: ``Filesystem*``, not
``Df*``. See ``docs/standards/naming-conventions.md#domain-driven-naming``
and :mod:`bcs.platform.errors`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bcs.platform.errors import PlatformError

if TYPE_CHECKING:
    from bcs.platform.models import CommandResult


class FilesystemError(PlatformError):
    """Base exception for all Filesystem Adapter failures.

    Raised when ``df`` exits non-zero in a way that is not recognisably
    an "environment cannot provide filesystem data" condition and zero
    filesystems could be parsed, or when the command succeeds but the
    output cannot be parsed into even one entry.

    Carries the originating :class:`~bcs.platform.models.CommandResult`
    for diagnosis, mirroring :class:`bcs.platform.errors.CommandExecutionError`'s
    own ``result`` attribute.
    """

    def __init__(self, message: str, *, result: CommandResult | None = None) -> None:
        super().__init__(message)
        self.result = result


class FilesystemUnavailableError(FilesystemError):
    """Raised when filesystem usage data cannot be read at all.

    ``df`` is present and executable, but the environment cannot
    provide filesystem data - e.g. the calling process lacks
    permission, or no filesystems could be enumerated in a restricted
    namespace - and zero filesystems could be parsed from its output.

    This is the *semantic* failure: "this environment cannot answer
    this question" - kept distinct from "the tool itself is broken,"
    which raises :class:`bcs.platform.errors.CommandNotFoundError` or
    :class:`bcs.platform.errors.CommandExecutionError` directly. It is
    also kept distinct from a *partial* failure: if ``df`` reports at
    least one filesystem successfully, that data is returned normally
    (with the failure signal attached to ``FilesystemUsageReport.raw_stderr``)
    rather than raised as this exception - see
    ``docs/FILESYSTEM_ADAPTER.md#adapter-responsibilities``.
    """


class FilesystemParseError(FilesystemError):
    """Raised when ``df`` output cannot be parsed into any filesystem.

    Either the command succeeded (zero exit code) but the output text
    contains no recognisable data row at all, or a data row was
    present but malformed (a row with too few fields, or a field that
    is neither a valid number nor, for inode fields, ``-``). This
    distinguishes "a real, if very unusual, output the parser
    tolerates" from "this isn't ``df``-shaped output at all" - a
    version incompatibility worth surfacing distinctly rather than
    silently returning a suspiciously-empty
    :class:`~bcs.platform.adapters.filesystem.models.FilesystemUsageReport`.
    """

    def __init__(self, message: str, *, text: str) -> None:
        super().__init__(message)
        self.text = text


__all__ = [
    "FilesystemError",
    "FilesystemParseError",
    "FilesystemUnavailableError",
]
