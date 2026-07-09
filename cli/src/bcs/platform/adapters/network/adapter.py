"""The Network Adapter: read-only orchestration layer.

This module is the **only** place in the
``bcs.platform.adapters.network`` subpackage that calls
:meth:`CommandRunner.run`, and the only module that knows the current
backend is ``ip``. The domain models
(:mod:`bcs.platform.adapters.network.models`) and the pure parser
(:mod:`bcs.platform.adapters.network.parser`) are kept free of any
execution concerns.

Design: ``docs/NETWORK_ADAPTER.md#adapter-responsibilities``, following
the exact architecture and style already established by
``bcs.platform.adapters.secureboot.adapter``/``.efi.adapter`` (accepted
per ``docs/decisions/0010-efi-adapter-read-only-scope.md``).
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from bcs.platform.adapters.network.errors import (
    NetworkError,
    NetworkParseError,
    NetworkUnavailableError,
)
from bcs.platform.adapters.network.models import NetworkInterfaceStatus
from bcs.platform.adapters.network.parser import parse_network_interfaces

if TYPE_CHECKING:
    from bcs.platform.execution import CommandRunner


# Recognised stderr fragments that indicate an environment that cannot
# provide network interface data (a netlink socket cannot be opened,
# permission denied, an inaccessible network namespace, etc.) - checked
# case-insensitively, mirroring the Secure Boot/EFI adapters' own
# ``_is_unavailable`` pattern set. See
# ``docs/NETWORK_ADAPTER.md#error-mapping``.
_UNAVAILABLE_PATTERNS: frozenset[str] = frozenset(
    [
        "network namespace not accessible",
        "cannot open netlink socket",
        "permission denied",
        "network is unreachable",
    ]
)


def _is_unavailable(stderr: str) -> bool:
    lower = stderr.lower()
    return any(pattern in lower for pattern in _UNAVAILABLE_PATTERNS)


def read_network_interfaces(
    runner: CommandRunner,
    *,
    timeout_seconds: float | None = 5.0,
) -> NetworkInterfaceStatus:
    """Read the system's current network interface status.

    This function is the **only** entry point in the Network Adapter
    that executes an external process. It:

    1. Calls ``runner.run()`` with ``["ip", "-json", "addr", "show"]``
       and ``LC_ALL=C LANG=C`` forced in the child environment.
    2. On success (exit 0): passes the captured stdout to
       :func:`~bcs.platform.adapters.network.parser.parse_network_interfaces`.
       A ``ValueError`` raised by the parser (invalid JSON, a
       non-array top level, or a malformed entry) is wrapped as
       :class:`~bcs.platform.adapters.network.errors.NetworkParseError`.
    3. On non-zero exit: raises
       :class:`~bcs.platform.adapters.network.errors.NetworkUnavailableError`
       if stderr is recognisably an "environment cannot provide
       network data" message, otherwise
       :class:`~bcs.platform.adapters.network.errors.NetworkError`.

    Parameters
    ----------
    runner:
        A :class:`~bcs.platform.execution.CommandRunner` instance.
        Supplied by the caller (dependency injection); the adapter
        never constructs one itself.
    timeout_seconds:
        Maximum wall-clock seconds to wait for ``ip`` to complete.
        Defaults to 5.0, matching the EFI and Secure Boot adapters'
        own defaults. Pass ``None`` to disable.

    Returns
    -------
    NetworkInterfaceStatus
        The parsed network interface snapshot. An empty JSON array is
        a valid, non-error result (``interfaces=()``).

    Raises
    ------
    CommandNotFoundError
        ``ip`` is not on ``PATH``.
    CommandTimeoutError
        The command exceeded ``timeout_seconds``.
    NetworkUnavailableError
        The environment cannot provide network interface data.
    NetworkParseError
        ``ip`` succeeded but its output could not be parsed.
    NetworkError
        Any other non-zero exit from ``ip``.
    """
    # Build a clean environment that forces C locale for stable output.
    # CommandRunner.run() *replaces* the child's environment entirely,
    # so we must copy os.environ and override LANG/LC_ALL rather than
    # passing only those two variables (which would drop PATH etc.).
    env = os.environ.copy()
    env["LANG"] = "C"
    env["LC_ALL"] = "C"

    result = runner.run(
        ["ip", "-json", "addr", "show"],
        timeout_seconds=timeout_seconds,
        check=False,
        env=env,
    )

    if result.exit_code != 0:
        if _is_unavailable(result.stderr):
            raise NetworkUnavailableError(
                "Network interface data is not available in this environment.",
                result=result,
            )
        raise NetworkError(
            f"ip exited with code {result.exit_code}.",
            result=result,
        )

    try:
        return parse_network_interfaces(result.stdout)
    except ValueError as exc:
        raise NetworkParseError(
            f"Failed to parse ip output: {exc}",
            text=result.stdout,
        ) from exc


__all__ = ["read_network_interfaces"]
