"""Domain-specific exceptions for the Network Adapter.

These exceptions extend the Platform Layer's existing hierarchy so that
a caller can ``except bcs.platform.errors.PlatformError`` once and catch
every Platform Layer failure (core or adapter) uniformly.

Naming follows the domain-driven naming rule: ``Network*``, not ``Ip*``.
See ``docs/standards/naming-conventions.md#domain-driven-naming``
and :mod:`bcs.platform.errors`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bcs.platform.errors import PlatformError

if TYPE_CHECKING:
    from bcs.platform.models import CommandResult


class NetworkError(PlatformError):
    """Base exception for all Network Adapter failures.

    Raised when ``ip`` exits with a non-zero code that is not
    recognisably a "network data unavailable" condition, or when the
    command succeeds but the output cannot be parsed at all.

    Carries the originating :class:`~bcs.platform.models.CommandResult`
    for diagnosis, mirroring :class:`bcs.platform.errors.CommandExecutionError`'s
    own ``result`` attribute.
    """

    def __init__(self, message: str, *, result: CommandResult | None = None) -> None:
        super().__init__(message)
        self.result = result


class NetworkUnavailableError(NetworkError):
    """Raised when network interface data cannot be read.

    The ``ip`` tool is present and executable, but the environment
    cannot provide network interface data — e.g. the calling process
    cannot open a netlink socket, lacks permission, or the network
    stack is unreachable.

    This is the *semantic* failure: "this environment cannot answer this
    question" — kept distinct from "the tool itself is broken," which
    raises :class:`bcs.platform.errors.CommandNotFoundError` or
    :class:`bcs.platform.errors.CommandExecutionError` directly.
    """


class NetworkParseError(NetworkError):
    """Raised when ``ip -json addr show`` output cannot be parsed.

    The command succeeded (zero exit code) but the output text is not
    valid JSON, is missing the expected top-level array, or contains a
    malformed entry (e.g. missing ``ifname``).  This distinguishes
    "a real, if very unusual, output the parser tolerates" from "this
    isn't ``ip``-shaped output at all" — a version incompatibility
    worth surfacing distinctly rather than silently returning a
    suspiciously-empty
    :class:`~bcs.platform.adapters.network.models.NetworkInterfaceStatus`.
    """

    def __init__(self, message: str, *, text: str) -> None:
        super().__init__(message)
        self.text = text


__all__ = [
    "NetworkError",
    "NetworkParseError",
    "NetworkUnavailableError",
]
