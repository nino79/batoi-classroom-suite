"""Domain-specific exceptions for the Storage Adapter.

These exceptions extend the Platform Layer's existing hierarchy so that
a caller can ``except bcs.platform.errors.PlatformError`` once and catch
every Platform Layer failure (core or adapter) uniformly.

Naming follows the domain-driven naming rule: ``Storage*``, not
``Lsblk*``/``Blkid*``/``Findmnt*``.  See
:ref:`domain-driven-naming` and :mod:`bcs.platform.errors`.

Error mapping (per ``docs/STORAGE_ADAPTER.md#error-handling``):

+----------------------+-----------------------------------------------+
| Tool failure         | Adapter action                                |
+======================+===============================================+
| ``lsblk`` not found  | Raise ``StorageUnavailableError("lsblk        |
|                      | not found")``                                 |
+----------------------+-----------------------------------------------+
| ``blkid`` not found  | Raise ``StorageUnavailableError("blkid       |
|                      | not found")``                                 |
+----------------------+-----------------------------------------------+
| ``findmnt`` not      | Raise ``StorageUnavailableError("findmnt      |
| found                | not found")``                                 |
+----------------------+-----------------------------------------------+
| Tool exits non-zero  | Raise ``StorageError(f"{tool} exited with      |
|                      | {exit_code}")``                               |
+----------------------+-----------------------------------------------+
| Tool times out       | Raise ``CommandTimeoutError`` (from            |
|                      | :mod:`bcs.platform.errors`) directly         |
+----------------------+-----------------------------------------------+
| Parser raises        | Wrap in ``StorageParseError``                  |
| exception           |                                               |
+----------------------+-----------------------------------------------+
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bcs.platform.errors import PlatformError

if TYPE_CHECKING:
    from bcs.platform.models import CommandResult


class StorageError(PlatformError):
    """Base exception for all Storage Adapter failures.

    Raised when a storage tool (``lsblk``, ``blkid``, ``findmnt``)
    exits with a non-zero code that is not recognisably a "storage
    data unavailable" condition, or when a command succeeds but the
    output cannot be parsed at all.

    Carries the originating :class:`~bcs.platform.models.CommandResult`
    for diagnosis, mirroring
    :class:`bcs.platform.errors.CommandExecutionError`'s own
    ``result`` attribute.
    """

    def __init__(self, message: str, *, result: CommandResult | None = None) -> None:
        super().__init__(message)
        self.result = result


class StorageUnavailableError(StorageError):
    """Raised when storage topology cannot be read.

    One or more of the required tools (``lsblk``, ``blkid``,
    ``findmnt``) is present and executable, but the environment cannot
    provide usable storage data — e.g. the calling process lacks
    permission to read a device node, or the device path does not
    exist.

    This is the *semantic* failure: "this environment cannot answer
    this question" — kept distinct from "the tool itself is broken,"
    which raises :class:`bcs.platform.errors.CommandNotFoundError` or
    :class:`bcs.platform.errors.CommandExecutionError` directly.
    """


class StorageParseError(StorageError):
    """Raised when storage-tool output cannot be parsed.

    A command succeeded (zero exit code) but the output text contains
    none of the patterns the parser recognises, or the JSON structure
    is malformed.  This distinguishes "a real, if very unusual, output
    the parser tolerates" from "this isn't ``lsblk``/``blkid``/``findmnt``
    -shaped output at all" — a version incompatibility or unexpected
    environment worth surfacing distinctly rather than silently
    returning a suspiciously-empty
    :class:`~bcs.platform.adapters.storage.models.StorageConfiguration`.
    """

    def __init__(self, message: str, *, text: str) -> None:
        super().__init__(message)
        self.text = text


__all__ = [
    "StorageError",
    "StorageParseError",
    "StorageUnavailableError",
]
