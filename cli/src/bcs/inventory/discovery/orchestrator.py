"""The Host Discovery Orchestrator's coordination logic.

Design: ``docs/HOST_DISCOVERY_ORCHESTRATOR.md#public-api`` and
``#error-propagation``, accepted per
``docs/decisions/0011-host-discovery-orchestrator.md``.

:class:`HostDiscoveryOrchestrator` is the coordination class the
data-holding types in :mod:`bcs.inventory.discovery.models`
(:class:`~bcs.inventory.discovery.models.HostDiscoveryAdapters`,
:class:`~bcs.inventory.discovery.models.HostDiscoverySnapshot`) were
built for: given a bundle of already-bound adapter callables, it calls
each configured one at most once, in a fixed order, and aggregates the
results into one immutable snapshot.

**Aggregation-only guarantee** (``docs/HOST_DISCOVERY_ORCHESTRATOR.md#aggregation-only-guarantee``):

- This module never imports ``subprocess``.
- This module never imports ``bcs.platform.execution.CommandRunner``.
- It never knows how any adapter works internally - it only ever calls
  the zero-argument callables :class:`HostDiscoveryAdapters` already
  holds, already bound to whatever they need by the composition root
  (not yet wired - see that document's own Dependency Injection
  Strategy). Its only structural dependency on the Platform Layer is
  on :class:`bcs.platform.errors.PlatformError`, the typed exception it
  isolates - a data/exception type, not an execution concern.
- It never interprets, ranks, selects, or merges adapter output -
  every :class:`~bcs.inventory.discovery.models.HostDiscoverySnapshot`
  field is exactly what the matching adapter returned, or absent.

**Error isolation** (``docs/HOST_DISCOVERY_ORCHESTRATOR.md#error-propagation``):
a :class:`~bcs.platform.errors.PlatformError` (or any subclass) raised
by one adapter leaves that domain's field absent and records one
``caveats`` entry; it never prevents the other domains from being
collected. Any other exception propagates unmodified out of
:meth:`HostDiscoveryOrchestrator.discover` - a genuine bug, not an
absence to isolate, per
``docs/standards/coding-standards.md#error-handling``'s "don't swallow
errors to make output quieter."
"""

from __future__ import annotations

from collections.abc import Callable

from bcs.inventory.discovery.models import HostDiscoveryAdapters, HostDiscoverySnapshot
from bcs.platform.errors import PlatformError


def _call_adapter[T](domain: str, adapter: Callable[[], T] | None, caveats: list[str]) -> T | None:
    """Call one adapter slot, isolating failure.

    Returns ``None`` if ``adapter`` is unset (no adapter wired for this
    domain - a configuration fact, not a failure, so nothing is
    appended to ``caveats``), or if calling it raised a
    :class:`PlatformError` (recorded as one ``caveats`` entry). Any
    other exception propagates unmodified - see this module's own
    docstring.
    """
    if adapter is None:
        return None
    try:
        return adapter()
    except PlatformError as exc:
        caveats.append(f"{domain}: {type(exc).__name__}: {exc}")
        return None


class HostDiscoveryOrchestrator:
    """Coordinates every wired Discovery adapter into one
    :class:`~bcs.inventory.discovery.models.HostDiscoverySnapshot`.

    Not a ``Protocol`` with multiple implementations, unlike
    ``CommandRunner``: there is exactly one coordination strategy (call
    every wired slot, isolate failures, aggregate), and the test seam
    is the :class:`HostDiscoveryAdapters` bundle it is constructed
    with, never the orchestrator class itself.
    """

    def __init__(self, adapters: HostDiscoveryAdapters) -> None:
        self._adapters = adapters

    def discover(self) -> HostDiscoverySnapshot:
        """Call every wired adapter at most once and aggregate the results.

        Adapters are called in a fixed order - ``efi``, ``storage``,
        ``secure_boot``, ``filesystem``, ``network``, ``cpu``,
        ``memory``, ``tpm`` - matching :class:`HostDiscoveryAdapters`'
        own field order. Expected to be called at most once per ``bcs``
        invocation; nothing prevents calling it more than once (each
        call re-invokes every wired adapter and produces a fresh,
        independent snapshot).
        """
        caveats: list[str] = []

        firmware_boot_configuration = _call_adapter("efi", self._adapters.efi, caveats)
        storage_topology = _call_adapter("storage", self._adapters.storage, caveats)
        secure_boot = _call_adapter("secure_boot", self._adapters.secure_boot, caveats)
        filesystem = _call_adapter("filesystem", self._adapters.filesystem, caveats)
        network_interfaces = _call_adapter("network", self._adapters.network, caveats)
        cpu = _call_adapter("cpu", self._adapters.cpu, caveats)
        memory = _call_adapter("memory", self._adapters.memory, caveats)
        tpm = _call_adapter("tpm", self._adapters.tpm, caveats)

        return HostDiscoverySnapshot(
            firmware_boot_configuration=firmware_boot_configuration,
            storage_topology=storage_topology,
            secure_boot=secure_boot,
            filesystem=filesystem,
            network=tuple(network_interfaces) if network_interfaces is not None else (),
            cpu=cpu,
            memory=memory,
            tpm=tpm,
            caveats=tuple(caveats),
        )


__all__ = ["HostDiscoveryOrchestrator"]
