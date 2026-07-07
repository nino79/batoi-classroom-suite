"""The Host Discovery Orchestrator's data-holding types.

Design: ``docs/HOST_DISCOVERY_ORCHESTRATOR.md``, accepted per
``docs/decisions/0011-host-discovery-orchestrator.md``.

Implemented so far: ``HostDiscoveryAdapters`` and ``HostDiscoverySnapshot``
(:mod:`bcs.inventory.discovery.models`) - the two data-holding types the
orchestrator will be built around. Per the accepted design, this
package will eventually also contain:

- ``orchestrator.py`` - ``HostDiscoveryOrchestrator``, the coordination
  class that calls each wired adapter and aggregates its output into a
  ``HostDiscoverySnapshot``.

Nothing in this package executes a process, imports ``subprocess``, or
imports ``bcs.platform.execution.CommandRunner`` at this stage.
"""

from bcs.inventory.discovery.models import HostDiscoveryAdapters, HostDiscoverySnapshot

__all__ = ["HostDiscoveryAdapters", "HostDiscoverySnapshot"]
