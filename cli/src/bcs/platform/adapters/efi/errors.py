"""Domain-specific exceptions for the EFI Adapter.

These exceptions extend the Platform Layer's existing hierarchy so that
a caller can ``except bcs.platform.errors.PlatformError`` once and catch
every Platform Layer failure (core or adapter) uniformly.

Naming follows the domain-driven naming rule: ``FirmwareBoot*``, not
``Efibootmgr*``.  See :ref:`domain-driven-naming` and
:mod:`bcs.platform.errors`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bcs.platform.errors import PlatformError

if TYPE_CHECKING:
    from bcs.platform.models import CommandResult


class FirmwareBootError(PlatformError):
    """Base exception for all EFI Adapter failures.

    Raised when ``efibootmgr`` exits with a non-zero code that is not
    recognizably a "EFI variables unavailable" condition, or when the
    command succeeds but the output cannot be parsed at all.

    Carries the originating :class:`~bcs.platform.models.CommandResult`
    for diagnosis, mirroring :class:`bcs.platform.errors.CommandExecutionError`'s
    own ``result`` attribute.
    """

    def __init__(self, message: str, *, result: CommandResult | None = None) -> None:
        super().__init__(message)
        self.result = result


class FirmwareBootUnavailableError(FirmwareBootError):
    """Raised when EFI boot configuration cannot be read.

    The ``efibootmgr`` tool is present and executable, but the
    environment cannot provide EFI boot variable data — e.g. the
    system is not booted in UEFI mode, or the calling process lacks
    permission to read ``/sys/firmware/efi/efivars``.

    This is the *semantic* failure: "this environment cannot answer this
    question" — kept distinct from "the tool itself is broken," which
    raises :class:`bcs.platform.errors.CommandNotFoundError` or
    :class:`bcs.platform.errors.CommandExecutionError` directly.
    """


class FirmwareBootParseError(FirmwareBootError):
    """Raised when ``efibootmgr`` output cannot be parsed.

    The command succeeded (zero exit code) but the output text contains
    none of the patterns the parser recognises.  This distinguishes
    "a real, if very unusual, output the parser tolerates" from "this
    isn't ``efibootmgr``-shaped output at all" — a version
    incompatibility worth surfacing distinctly rather than silently
    returning a suspiciously-empty
    :class:`~bcs.platform.adapters.efi.models.FirmwareBootConfiguration`.
    """

    def __init__(self, message: str, *, text: str) -> None:
        super().__init__(message)
        self.text = text


__all__ = [
    "FirmwareBootError",
    "FirmwareBootParseError",
    "FirmwareBootUnavailableError",
]
