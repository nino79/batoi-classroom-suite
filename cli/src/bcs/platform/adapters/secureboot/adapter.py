"""The Secure Boot Adapter: read-only orchestration layer.

This module is the **only** place in the
``bcs.platform.adapters.secureboot`` subpackage that calls
:meth:`CommandRunner.run`, and the only module that knows the current
backend is ``mokutil``. The domain models
(:mod:`bcs.platform.adapters.secureboot.models`) and the pure parser
(:mod:`bcs.platform.adapters.secureboot.parser`) are kept free of any
execution concerns.

Design: ``docs/SECURE_BOOT_ADAPTER.md#adapter-responsibilities``,
following the exact architecture and style already established by
``bcs.platform.adapters.efi.adapter`` (accepted per
``docs/decisions/0010-efi-adapter-read-only-scope.md``).
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from bcs.platform.adapters.secureboot.errors import (
    SecureBootError,
    SecureBootParseError,
    SecureBootUnavailableError,
)
from bcs.platform.adapters.secureboot.models import SecureBootState, SecureBootStatus
from bcs.platform.adapters.secureboot.parser import parse_secure_boot_status

if TYPE_CHECKING:
    from bcs.platform.execution import CommandRunner


# Recognised stderr fragments that indicate an environment that cannot
# provide Secure Boot data (not a UEFI system, efivarfs not mounted,
# permission denied, etc.) - checked case-insensitively, mirroring the
# EFI adapter's own ``_is_unavailable`` pattern set.
_UNAVAILABLE_PATTERNS: frozenset[str] = frozenset(
    [
        "efi variables are not supported",
        "not supported on this system",
        "efivarfs not mounted",
        "permission denied",
        "operation not permitted",
        "no such file or directory",
        "failed to read",
    ]
)


def _is_unavailable(stderr: str) -> bool:
    lower = stderr.lower()
    return any(pattern in lower for pattern in _UNAVAILABLE_PATTERNS)


def read_secure_boot_status(
    runner: CommandRunner,
    *,
    timeout_seconds: float | None = 5.0,
) -> SecureBootStatus:
    """Read the system's current firmware Secure Boot state.

    This function is the **only** entry point in the Secure Boot
    Adapter that executes an external process. It:

    1. Calls ``runner.run()`` with ``["mokutil", "--sb-state"]`` and
       ``LC_ALL=C LANG=C`` forced in the child environment.
    2. On success (exit 0): passes the captured stdout to
       :func:`~bcs.platform.adapters.secureboot.parser.parse_secure_boot_status`.
       If the parsed result has ``state == UNKNOWN`` **and**
       ``setup_mode is None`` - meaning the source text contained no
       recognized line at all - raises
       :class:`~bcs.platform.adapters.secureboot.errors.SecureBootParseError`,
       per [docs/SECURE_BOOT_ADAPTER.md § Adapter
       Responsibilities](../../../../../docs/SECURE_BOOT_ADAPTER.md#adapter-responsibilities)
       point 4.
    3. On non-zero exit: raises
       :class:`~bcs.platform.adapters.secureboot.errors.SecureBootUnavailableError`
       if stderr is recognisably an "environment cannot provide Secure
       Boot data" message, otherwise
       :class:`~bcs.platform.adapters.secureboot.errors.SecureBootError`.

    Parameters
    ----------
    runner:
        A :class:`~bcs.platform.execution.CommandRunner` instance.
        Supplied by the caller (dependency injection); the adapter
        never constructs one itself.
    timeout_seconds:
        Maximum wall-clock seconds to wait for ``mokutil`` to
        complete. Defaults to 5.0, matching the EFI Adapter's own
        default. Pass ``None`` to disable.

    Returns
    -------
    SecureBootStatus
        The parsed Secure Boot state snapshot.

    Raises
    ------
    CommandNotFoundError
        ``mokutil`` is not on ``PATH``.
    CommandTimeoutError
        The command exceeded ``timeout_seconds``.
    SecureBootUnavailableError
        The environment cannot provide Secure Boot data.
    SecureBootParseError
        ``mokutil`` succeeded but its output contained no recognized
        line at all.
    SecureBootError
        Any other non-zero exit from ``mokutil``.
    """
    # Build a clean environment that forces C locale for stable output.
    # CommandRunner.run() *replaces* the child's environment entirely,
    # so we must copy os.environ and override LANG/LC_ALL rather than
    # passing only those two variables (which would drop PATH etc.).
    env = os.environ.copy()
    env["LANG"] = "C"
    env["LC_ALL"] = "C"

    result = runner.run(
        ["mokutil", "--sb-state"],
        timeout_seconds=timeout_seconds,
        check=False,
        env=env,
    )

    if result.exit_code != 0:
        if _is_unavailable(result.stderr):
            raise SecureBootUnavailableError(
                "Secure Boot state is not available in this environment.",
                result=result,
            )
        raise SecureBootError(
            f"mokutil exited with code {result.exit_code}.",
            result=result,
        )

    try:
        status = parse_secure_boot_status(result.stdout)
    except ValueError as exc:
        raise SecureBootParseError(
            f"Failed to parse mokutil output: {exc}",
            text=result.stdout,
        ) from exc

    if status.state == SecureBootState.UNKNOWN and status.setup_mode is None:
        raise SecureBootParseError(
            "mokutil output contained no recognized Secure Boot state line.",
            text=result.stdout,
        )

    return status


__all__ = ["read_secure_boot_status"]
