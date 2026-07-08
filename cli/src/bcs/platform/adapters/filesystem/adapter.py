"""The Filesystem Adapter: read-only orchestration layer.

This module is the **only** place in the
``bcs.platform.adapters.filesystem`` subpackage that calls
:meth:`CommandRunner.run`, and the only module that knows the current
backend is ``df``. The domain models
(:mod:`bcs.platform.adapters.filesystem.models`) and the pure parser
(:mod:`bcs.platform.adapters.filesystem.parser`) are kept free of any
execution concerns.

Design: ``docs/FILESYSTEM_ADAPTER.md#adapter-responsibilities``,
following the exact architecture and style already established by
``bcs.platform.adapters.efi.adapter``/``.storage.adapter``/``.secureboot.adapter``.

**The one adapter-level judgment call unique to this adapter**: on
*any* exit code, if the parser returns at least one
:class:`~bcs.platform.adapters.filesystem.models.FilesystemUsage`, that
data is returned normally - with ``result.stderr`` attached to
``FilesystemUsageReport.raw_stderr`` verbatim, even when empty -
rather than being discarded because ``df`` exited non-zero. This keeps
a partial ``df`` failure (one stale mount causing a non-zero exit
while every other filesystem was still successfully read) observable
on the returned value instead of silently lost - see
``docs/FILESYSTEM_ADAPTER.md#relationship-to-the-host-discovery-orchestrators-caveats-model``.
Only when the parser returns *zero* entries does this adapter fall
back to the typed-exception error mapping every sibling adapter uses.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from bcs.platform.adapters.filesystem.errors import (
    FilesystemError,
    FilesystemParseError,
    FilesystemUnavailableError,
)
from bcs.platform.adapters.filesystem.models import FilesystemUsageReport
from bcs.platform.adapters.filesystem.parser import parse_filesystem_usage

if TYPE_CHECKING:
    from bcs.platform.execution import CommandRunner


# Recognised stderr fragments that indicate an environment that cannot
# provide filesystem data (permission denied, nothing mounted in a
# restricted namespace, etc.) - checked case-insensitively, mirroring
# every sibling adapter's own "_is_unavailable" pattern set.
_UNAVAILABLE_PATTERNS: frozenset[str] = frozenset(
    [
        "permission denied",
        "operation not permitted",
        "no such file or directory",
        "no file systems processed",
        "cannot read table of mounted file systems",
    ]
)


def _is_unavailable(stderr: str) -> bool:
    lower = stderr.lower()
    return any(pattern in lower for pattern in _UNAVAILABLE_PATTERNS)


def read_filesystem_usage(
    runner: CommandRunner,
    *,
    timeout_seconds: float | None = 10.0,
) -> FilesystemUsageReport:
    """Read the system's current filesystem usage and capacity.

    This function is the **only** entry point in the Filesystem
    Adapter that executes an external process. It:

    1. Calls ``runner.run()`` with
       ``["df", "--output=source,fstype,itotal,iused,iavail,size,used,avail,target", "-B1", "-a"]``
       and ``LC_ALL=C LANG=C`` forced in the child environment.
    2. On any exit code: passes ``result.stdout`` to
       :func:`~bcs.platform.adapters.filesystem.parser.parse_filesystem_usage`.
       If it returns at least one
       :class:`~bcs.platform.adapters.filesystem.models.FilesystemUsage`,
       returns a copy of that report with ``raw_stderr`` set to
       ``result.stderr`` (verbatim, even when empty) - regardless of
       exit code. See ``docs/FILESYSTEM_ADAPTER.md#adapter-responsibilities``
       point 4.
    3. If the parser raised ``ValueError`` (a malformed row/field):
       raises
       :class:`~bcs.platform.adapters.filesystem.errors.FilesystemParseError`,
       chained.
    4. If the parser returned zero entries: raises
       :class:`~bcs.platform.adapters.filesystem.errors.FilesystemUnavailableError`
       if the non-zero exit's stderr is recognisably an "environment
       cannot provide filesystem data" message,
       :class:`~bcs.platform.adapters.filesystem.errors.FilesystemError`
       for any other non-zero exit, or
       :class:`~bcs.platform.adapters.filesystem.errors.FilesystemParseError`
       if the exit was zero but nothing could be parsed.

    Parameters
    ----------
    runner:
        A :class:`~bcs.platform.execution.CommandRunner` instance.
        Supplied by the caller (dependency injection); the adapter
        never constructs one itself.
    timeout_seconds:
        Maximum wall-clock seconds to wait for ``df`` to complete.
        Defaults to 10.0, matching the Storage Adapter's own budget -
        ``df`` enumerating every mounted filesystem is a slightly
        heavier sweep than reading one NVRAM/EFI variable, and ``df``
        is the one adapter in this family with a well-known real-world
        hang scenario (a stuck network/stale-handle mount). Pass
        ``None`` to disable.

    Returns
    -------
    FilesystemUsageReport
        The parsed filesystem usage snapshot, with ``raw_stderr``
        attached.

    Raises
    ------
    CommandNotFoundError
        ``df`` is not on ``PATH``.
    CommandTimeoutError
        The command exceeded ``timeout_seconds``.
    FilesystemUnavailableError
        The environment cannot provide filesystem data, and zero
        filesystems could be parsed.
    FilesystemParseError
        ``df``'s output could not be parsed into any filesystem at
        all, or contained a malformed row/field.
    FilesystemError
        Any other non-zero exit from ``df`` with zero filesystems
        parsed.
    """
    # Build a clean environment that forces C locale for stable output.
    # CommandRunner.run() *replaces* the child's environment entirely,
    # so we must copy os.environ and override LANG/LC_ALL rather than
    # passing only those two variables (which would drop PATH etc.).
    env = os.environ.copy()
    env["LANG"] = "C"
    env["LC_ALL"] = "C"

    result = runner.run(
        ["df", "--output=source,fstype,itotal,iused,iavail,size,used,avail,target", "-B1", "-a"],
        timeout_seconds=timeout_seconds,
        check=False,
        env=env,
    )

    try:
        report = parse_filesystem_usage(result.stdout)
    except ValueError as exc:
        raise FilesystemParseError(
            f"Failed to parse df output: {exc}",
            text=result.stdout,
        ) from exc

    if report.filesystems:
        return report.model_copy(update={"raw_stderr": result.stderr})

    if result.exit_code != 0:
        if _is_unavailable(result.stderr):
            raise FilesystemUnavailableError(
                "Filesystem usage data is not available in this environment.",
                result=result,
            )
        raise FilesystemError(
            f"df exited with code {result.exit_code}.",
            result=result,
        )

    raise FilesystemParseError(
        "df output contained no recognizable filesystem usage data.",
        text=result.stdout,
    )


__all__ = ["read_filesystem_usage"]
