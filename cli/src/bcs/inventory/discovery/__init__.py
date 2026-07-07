"""The Host Discovery Orchestrator.

Design: ``docs/HOST_DISCOVERY_ORCHESTRATOR.md``, accepted per
``docs/decisions/0011-host-discovery-orchestrator.md``.

Implemented: ``HostDiscoveryAdapters`` and ``HostDiscoverySnapshot``
(:mod:`bcs.inventory.discovery.models`) - the two data-holding types -
and ``HostDiscoveryOrchestrator`` (:mod:`bcs.inventory.discovery.orchestrator`),
the coordination class that calls each wired adapter at most once and
aggregates its output into a ``HostDiscoverySnapshot``.

Nothing in this package executes a process, imports ``subprocess``, or
imports ``bcs.platform.execution.CommandRunner``.
``bcs.inventory.service.collect_host_inventory()`` accepts an optional
``HostDiscoveryOrchestrator`` (see
``docs/HOST_DISCOVERY_ORCHESTRATOR.md#relationship-to-host-inventory---implemented``).
Composition-root wiring (binding real adapters into a
``HostDiscoveryAdapters`` and constructing a ``HostDiscoveryOrchestrator``
from it) and ``RuntimeContext`` integration do not exist yet.
"""

from bcs.inventory.discovery.models import HostDiscoveryAdapters, HostDiscoverySnapshot
from bcs.inventory.discovery.orchestrator import HostDiscoveryOrchestrator

__all__ = ["HostDiscoveryAdapters", "HostDiscoveryOrchestrator", "HostDiscoverySnapshot"]
