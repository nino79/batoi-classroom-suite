"""The Storage Adapter: read-only orchestration layer.

This module is the **only** place in the ``bcs.platform.adapters.storage``
subpackage that calls :meth:`CommandRunner.run`. The domain models
(:mod:`bcs.platform.adapters.storage.models`) and the pure parser
(:mod:`bcs.platform.adapters.storage.parser`) are kept free of any
execution concerns - this module contains **no parsing logic** of its
own; it only executes the three storage tools, collects their output,
and hands it to :func:`~bcs.platform.adapters.storage.parser.parse_storage_topology`.

Design: ``docs/STORAGE_ADAPTER.md#adapter-responsibilities``, following
the exact architecture and style already established by
``bcs.platform.adapters.efi.adapter`` (accepted per
``docs/decisions/0010-efi-adapter-read-only-scope.md``).

**Amended during implementation, to match the EFI adapter's own
precedent exactly:** ``CommandNotFoundError``/``CommandTimeoutError``
(raised by ``CommandRunner.run()`` itself when a tool is missing from
``PATH`` or exceeds its timeout) propagate **unchanged** - this adapter
does not wrap them in ``StorageUnavailableError``, mirroring
``bcs.platform.adapters.efi.adapter``'s own documented choice not to
translate ``CommandNotFoundError``/``CommandTimeoutError`` into
``FirmwareBoot*Error``. This is also the reading consistent with
``StorageUnavailableError``'s own docstring
(:mod:`bcs.platform.adapters.storage.errors`): "one or more of the
required tools *is present and executable*, but the environment cannot
provide usable storage data" - a tool missing from ``PATH`` entirely is
a different, already-typed condition (``CommandNotFoundError``), not
this adapter's concern to re-wrap.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from bcs.platform.adapters.storage.errors import (
    StorageError,
    StorageParseError,
    StorageUnavailableError,
)
from bcs.platform.adapters.storage.models import StorageConfiguration
from bcs.platform.adapters.storage.parser import parse_storage_topology

if TYPE_CHECKING:
    from bcs.platform.execution import CommandRunner

# Recognised stderr fragments that indicate a tool is present and
# executable but the environment cannot provide usable storage data
# (permission denied, a device node that vanished, etc.) - checked
# case-insensitively, mirroring the EFI adapter's own
# ``_is_unavailable`` pattern set, generalised across three tools
# rather than one.
_UNAVAILABLE_PATTERNS: frozenset[str] = frozenset(
    [
        "permission denied",
        "operation not permitted",
        "no such file or directory",
        "no such device",
        "no medium found",
        "cannot open",
        "not authorized",
    ]
)


def _is_unavailable(stderr: str) -> bool:
    lower = stderr.lower()
    return any(pattern in lower for pattern in _UNAVAILABLE_PATTERNS)


def _run_tool(
    runner: CommandRunner,
    tool: str,
    args: list[str],
    *,
    timeout_seconds: float | None,
    env: dict[str, str],
) -> str:
    """Run one storage tool and return its stdout.

    ``CommandNotFoundError``/``CommandTimeoutError`` raised by
    ``runner.run()`` itself propagate unchanged - see this module's
    own docstring for why. A non-zero exit is translated into
    :class:`~bcs.platform.adapters.storage.errors.StorageUnavailableError`
    (recognisable "environment cannot provide this data" stderr) or the
    base :class:`~bcs.platform.adapters.storage.errors.StorageError`
    (anything else), each carrying the full result for diagnosis.
    """
    result = runner.run([tool, *args], timeout_seconds=timeout_seconds, check=False, env=env)
    if result.exit_code != 0:
        if _is_unavailable(result.stderr):
            raise StorageUnavailableError(
                f"{tool} could not provide storage data in this environment.",
                result=result,
            )
        raise StorageError(
            f"{tool} exited with code {result.exit_code}.",
            result=result,
        )
    return result.stdout


def read_storage_topology(
    runner: CommandRunner,
    *,
    timeout_seconds: float | None = 10.0,
) -> StorageConfiguration:
    """Read the system's current storage topology.

    This function is the **only** entry point in the Storage Adapter
    that executes an external process. It:

    1. Calls ``runner.run()`` three times - ``["lsblk", "-J", "-b"]``,
       ``["blkid", "-p", "-o", "json"]``, ``["findmnt", "-J"]`` - each
       with ``LC_ALL=C LANG=C`` forced in the child environment and
       ``check=False``.
    2. On success (exit 0 for all three): passes the three captured
       stdout strings to
       :func:`~bcs.platform.adapters.storage.parser.parse_storage_topology`.
    3. On a non-zero exit from any tool: raises
       :class:`~bcs.platform.adapters.storage.errors.StorageUnavailableError`
       if stderr is recognisably an "environment cannot provide this
       data" message, otherwise
       :class:`~bcs.platform.adapters.storage.errors.StorageError`.
       The remaining tools are not run once one has failed.
    4. On parser failure: raises
       :class:`~bcs.platform.adapters.storage.errors.StorageParseError`,
       chained from the original ``ValueError``.

    Parameters
    ----------
    runner:
        A :class:`~bcs.platform.execution.CommandRunner` instance.
        Supplied by the caller (dependency injection); the adapter
        never constructs one itself.
    timeout_seconds:
        Maximum wall-clock seconds to wait for each tool to complete,
        applied identically to all three invocations
        (``docs/STORAGE_ADAPTER.md#command-execution``). Defaults to
        10.0. Pass ``None`` to disable.

    Returns
    -------
    StorageConfiguration
        The parsed storage topology snapshot.

    Raises
    ------
    CommandNotFoundError
        One of ``lsblk``/``blkid``/``findmnt`` is not on ``PATH``.
    CommandTimeoutError
        A tool exceeded ``timeout_seconds``.
    StorageUnavailableError
        The environment cannot provide storage data (permission
        denied, a device node that vanished, etc.).
    StorageParseError
        All three tools succeeded but their output could not be
        parsed.
    StorageError
        Any other non-zero exit from a storage tool.
    """
    env = os.environ.copy()
    env["LANG"] = "C"
    env["LC_ALL"] = "C"

    lsblk_output = _run_tool(
        runner, "lsblk", ["-J", "-b"], timeout_seconds=timeout_seconds, env=env
    )
    blkid_output = _run_tool(
        runner, "blkid", ["-p", "-o", "json"], timeout_seconds=timeout_seconds, env=env
    )
    findmnt_output = _run_tool(runner, "findmnt", ["-J"], timeout_seconds=timeout_seconds, env=env)

    try:
        return parse_storage_topology(lsblk_output, blkid_output, findmnt_output)
    except ValueError as exc:
        text = (
            f"lsblk:\n{lsblk_output}\n---\nblkid:\n{blkid_output}\n---\nfindmnt:\n{findmnt_output}"
        )
        raise StorageParseError(
            f"Failed to parse storage topology: {exc}",
            text=text,
        ) from exc


__all__ = ["read_storage_topology"]
