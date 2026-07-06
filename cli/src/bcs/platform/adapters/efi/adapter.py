"""The EFI Adapter: read-only orchestration layer.

This module is the **only** place in the ``bcs.platform.adapters.efi``
subpackage that calls :meth:`CommandRunner.run`.  The domain models
(:mod:`bcs.platform.adapters.efi.models`) and the pure parser
(:mod:`bcs.platform.adapters.efi.parser`) are kept free of any
execution concerns.

Design: :ref:`efi-adapter`, accepted per
:commit:`docs/decisions/0010-efi-adapter-read-only-scope.md <nino79/batoi-classroom-suite>`.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from bcs.platform.adapters.efi.errors import (
    FirmwareBootError,
    FirmwareBootParseError,
    FirmwareBootUnavailableError,
)
from bcs.platform.adapters.efi.models import FirmwareBootConfiguration
from bcs.platform.adapters.efi.parser import parse_firmware_boot_configuration

if TYPE_CHECKING:
    from bcs.platform.execution import CommandRunner


# Recognised stderr fragments that indicate an environment that cannot
# provide EFI boot-variable data (not a UEFI system, permission denied,
# efivars not mounted, etc.).  Checked case-insensitively.
_UNAVAILABLE_PATTERNS: frozenset[str] = frozenset(
    [
        "efivars not mounted",
        "efivarfs not mounted",
        "permission denied",
        "operation not permitted",
        "no such file or directory",
        "efi system partition",
        "boot variable",
        "efi variables",
        "not supported",
    ]
)


def _is_unavailable(stderr: str) -> bool:
    lower = stderr.lower()
    return any(pat in lower for pat in _UNAVAILABLE_PATTERNS)


def read_firmware_boot_configuration(
    runner: CommandRunner,
    *,
    timeout_seconds: float | None = 30.0,
) -> FirmwareBootConfiguration:
    """Read the system's current UEFI firmware boot configuration.

    This function is the **only** entry point in the EFI Adapter that
    executes an external process.  It:

    1. Calls ``runner.run()`` with ``["efibootmgr", "-v"]`` and
       ``LC_ALL=C LANG=C`` forced in the child environment.
    2. On success (exit 0): passes the captured stdout to
       :func:`~bcs.platform.adapters.efi.parser.parse_firmware_boot_configuration`.
    3. On non-zero exit: raises :class:`FirmwareBootUnavailableError`
       if stderr is recognisably an "EFI variables unavailable" message,
       otherwise :class:`FirmwareBootError`.
    4. On parser failure: raises :class:`FirmwareBootParseError`.

    Parameters
    ----------
    runner:
        A :class:`~bcs.platform.execution.CommandRunner` instance.
        Supplied by the caller (dependency injection); the adapter
        never constructs one itself.
    timeout_seconds:
        Maximum wall-clock seconds to wait for ``efibootmgr`` to
        complete.  Defaults to 30.0.  Pass ``None`` to disable.

    Returns
    -------
    FirmwareBootConfiguration
        The parsed boot configuration snapshot.

    Raises
    ------
    CommandNotFoundError
        ``efibootmgr`` is not on ``PATH``.
    CommandTimeoutError
        The command exceeded ``timeout_seconds``.
    FirmwareBootUnavailableError
        The environment cannot provide EFI boot-variable data.
    FirmwareBootParseError
        ``efibootmgr`` succeeded but its output is unrecognisable.
    FirmwareBootError
        Any other non-zero exit from ``efibootmgr``.
    """
    # Build a clean environment that forces C locale for stable output.
    # CommandRunner.run() *replaces* the child's environment entirely,
    # so we must copy os.environ and override LANG/LC_ALL rather than
    # passing only those two variables (which would drop PATH etc.).
    env = os.environ.copy()
    env["LANG"] = "C"
    env["LC_ALL"] = "C"

    result = runner.run(
        ["efibootmgr", "-v"],
        timeout_seconds=timeout_seconds,
        check=False,
        env=env,
    )

    if result.exit_code != 0:
        if _is_unavailable(result.stderr):
            raise FirmwareBootUnavailableError(
                "EFI boot variables are not available in this environment.",
                result=result,
            )
        raise FirmwareBootError(
            f"efibootmgr exited with code {result.exit_code}.",
            result=result,
        )

    try:
        return parse_firmware_boot_configuration(result.stdout)
    except ValueError as exc:
        raise FirmwareBootParseError(
            f"Failed to parse efibootmgr output: {exc}",
            text=result.stdout,
        ) from exc


__all__ = ["read_firmware_boot_configuration"]
