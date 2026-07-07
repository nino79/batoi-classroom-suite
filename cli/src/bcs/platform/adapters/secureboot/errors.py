"""Domain-specific exceptions for the Secure Boot Adapter.

These exceptions extend the Platform Layer's existing hierarchy so that
a caller can ``except bcs.platform.errors.PlatformError`` once and catch
every Platform Layer failure (core or adapter) uniformly.

Naming follows the domain-driven naming rule: ``SecureBoot*``, not
``Mokutil*``.  See :ref:`domain-driven-naming` and
:mod:`bcs.platform.errors`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bcs.platform.errors import PlatformError

if TYPE_CHECKING:
    from bcs.platform.models import CommandResult


class SecureBootError(PlatformError):
    """Base exception for all Secure Boot Adapter failures.

    Raised when ``mokutil`` exits with a non-zero code that is not
    recognisably a "Secure Boot data unavailable" condition, or when
    the command succeeds but the output cannot be parsed at all.

    Carries the originating :class:`~bcs.platform.models.CommandResult`
    for diagnosis, mirroring :class:`bcs.platform.errors.CommandExecutionError`'s
    own ``result`` attribute.
    """

    def __init__(self, message: str, *, result: CommandResult | None = None) -> None:
        super().__init__(message)
        self.result = result


class SecureBootUnavailableError(SecureBootError):
    """Raised when Secure Boot state cannot be read.

    The ``mokutil`` tool is present and executable, but the
    environment cannot provide Secure Boot data — e.g. the system
    does not support Secure Boot, or the calling process lacks
    permission to query the firmware state.

    This is the *semantic* failure: "this environment cannot answer this
    question" — kept distinct from "the tool itself is broken," which
    raises :class:`bcs.platform.errors.CommandNotFoundError` or
    :class:`bcs.platform.errors.CommandExecutionError` directly.
    """


class SecureBootParseError(SecureBootError):
    """Raised when ``mokutil`` output cannot be parsed.

    The command succeeded (zero exit code) but the output text contains
    none of the patterns the parser recognises.  This distinguishes
    "a real, if very unusual, output the parser tolerates" from "this
    isn't ``mokutil``-shaped output at all" — a version
    incompatibility worth surfacing distinctly rather than silently
    returning a suspiciously-empty
    :class:`~bcs.platform.adapters.secureboot.models.SecureBootStatus`.
    """

    def __init__(self, message: str, *, text: str) -> None:
        super().__init__(message)
        self.text = text


__all__ = [
    "SecureBootError",
    "SecureBootParseError",
    "SecureBootUnavailableError",
]
