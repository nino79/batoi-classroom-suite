"""Immutable domain models for the Host Discovery Orchestrator.

Design: ``docs/HOST_DISCOVERY_ORCHESTRATOR.md#public-api``, accepted
per ``docs/decisions/0011-host-discovery-orchestrator.md``.

This module contains the two data-holding types
:class:`HostDiscoveryOrchestrator` (``orchestrator.py``, implemented)
is built around:

- :class:`HostDiscoveryAdapters` - a frozen dependency-injection bundle
  of already-bound, zero-argument adapter callables, one named slot per
  Discovery domain. Built once, at the composition root
  (``bcs.app.main()``), and passed to the orchestrator's constructor -
  see
  ``docs/HOST_DISCOVERY_ORCHESTRATOR.md#dependency-injection-strategy---implemented``.
- :class:`HostDiscoverySnapshot` - the frozen, JSON-serializable
  aggregate the orchestrator produces - its only output type,
  deliberately distinct from ``HostInventory`` itself (which has
  fields, ``identity``/``tooling``, that are not Discovery domains -
  see ``docs/HOST_DISCOVERY_ORCHESTRATOR.md#relationship-to-host-inventory---implemented``).

Neither type executes a process, imports ``subprocess``, or imports
``bcs.platform.execution.CommandRunner`` - see
``docs/HOST_DISCOVERY_ORCHESTRATOR.md#aggregation-only-guarantee``.
Eight explicit, named, optional slots - not a dynamic registry, not a
plugin mechanism, not a dictionary keyed by strings - mirroring the
same reasoning ``docs/HOST_INVENTORY.md`` already used to decline a
``Collector`` protocol/registry for the same category of extensibility
question.

**``network`` typed to the Network Adapter's own model**: now that the
Network Adapter (``bcs.platform.adapters.network``) is accepted and
implemented, ``HostDiscoveryAdapters.network``/``HostDiscoverySnapshot.network``
are typed against its concrete ``NetworkInterfaceStatus`` model - the
same treatment ``efi``/``storage``/``secure_boot``/``filesystem``
already received once their own adapters reached acceptance. (An
earlier revision of this module typed the slot against
``list[NetworkInterface]``, matching the pre-adapter
``bcs.inventory.collectors.collect_network`` binding; see
``docs/NETWORK_ADAPTER.md#relationship-to-host-discovery-orchestrator``
for the narrowing this superseded.)
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

from bcs.inventory.models import CpuInfo, MemoryInfo
from bcs.platform.adapters.efi.models import FirmwareBootConfiguration
from bcs.platform.adapters.filesystem.models import FilesystemUsageReport
from bcs.platform.adapters.network.models import NetworkInterfaceStatus
from bcs.platform.adapters.secureboot.models import SecureBootStatus
from bcs.platform.adapters.storage.models import StorageConfiguration


@dataclass(frozen=True)
class HostDiscoveryAdapters:
    """A dependency-injection bundle of already-bound, zero-argument
    Discovery adapter callables - one named slot per domain.

    Every field is **optional** and defaults to ``None``, meaning "no
    adapter wired in for this domain in this build" - never an error by
    itself. Fields for domains with an accepted, implemented adapter
    (``efi``, ``storage``, ``secure_boot``, ``filesystem``, ``network``)
    are typed against that adapter's own return model; the ``tpm`` field
    is typed ``Callable[[], object] | None`` - deliberately generic,
    since there is no accepted adapter design for that domain yet.
    ``cpu``/``memory`` reuse the existing, already-implemented
    ``bcs.inventory.collectors`` functions as-is (``collect_cpu``/
    ``collect_memory`` are already zero-argument and satisfy these
    slots' types directly - no binding needed).

    Not a Pydantic model: this bundle holds callables, not serializable
    data. A frozen ``dataclass`` mirrors ``bcs.context.RuntimeContext``'s
    own precedent exactly - a frozen bundle of collaborators, built once
    at the composition root.
    """

    efi: Callable[[], FirmwareBootConfiguration] | None = None
    storage: Callable[[], StorageConfiguration] | None = None
    secure_boot: Callable[[], SecureBootStatus] | None = None
    filesystem: Callable[[], FilesystemUsageReport] | None = None
    network: Callable[[], NetworkInterfaceStatus] | None = None
    cpu: Callable[[], CpuInfo] | None = None
    memory: Callable[[], MemoryInfo] | None = None
    tpm: Callable[[], object] | None = None


class HostDiscoverySnapshot(BaseModel):
    """The Host Discovery Orchestrator's aggregate output - one field per
    Discovery domain, mirroring :class:`HostDiscoveryAdapters` exactly.

    Field-for-field, every payload field is either exactly what the
    matching :class:`HostDiscoveryAdapters` slot's callable returned,
    unmodified, or absent if that slot was unset or its call failed.
    Like ``CommandResult``, ``FirmwareBootConfiguration``, and
    ``StorageConfiguration``, this model deliberately does **not**
    carry its own ``schemaVersion`` - it is never a ``bcs`` command's
    own top-level payload; it is always consumed by
    ``bcs.inventory.service.collect_host_inventory()`` on its way into
    ``HostInventory``, once that integration exists.

    **Unconditionally hashable.** Every field here is either a frozen
    model with only hashable fields (tuples, not lists, throughout -
    including ``network``'s ``NetworkInterfaceStatus``, whose own
    ``NetworkInterface.ip_addresses`` is a ``tuple[str, ...]``, unlike
    ``bcs.inventory.models.NetworkInterface``'s ``list[str]``), ``None``,
    or an ``object``-typed opaque value. **Historical note:** before
    ``network`` was typed to ``NetworkInterfaceStatus``, it held
    ``bcs.inventory.models.NetworkInterface`` instances instead, whose
    ``list``-typed ``ip_addresses`` field made any snapshot with at
    least one network interface unhashable - the same limitation
    ``HostInventory`` itself still has. That caveat no longer applies to
    this model.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    firmware_boot_configuration: FirmwareBootConfiguration | None = Field(
        alias="firmwareBootConfiguration",
        default=None,
        description="From the `efi` adapter slot. None if unset or its call failed.",
    )
    storage_topology: StorageConfiguration | None = Field(
        alias="storageTopology",
        default=None,
        description="From the `storage` adapter slot. None if unset or its call failed.",
    )
    secure_boot: SecureBootStatus | None = Field(
        alias="secureBoot",
        default=None,
        description="From the `secure_boot` adapter slot. None if unset or its call failed.",
    )
    filesystem: FilesystemUsageReport | None = Field(
        default=None,
        description="From the `filesystem` adapter slot. None if unset or its call failed.",
    )
    network: NetworkInterfaceStatus | None = Field(
        default=None,
        description="From the `network` adapter slot. None if unset or its call failed.",
    )
    cpu: CpuInfo | None = Field(
        default=None,
        description="From the `cpu` adapter slot. None if unset or its call failed.",
    )
    memory: MemoryInfo | None = Field(
        default=None,
        description="From the `memory` adapter slot. None if unset or its call failed.",
    )
    tpm: object | None = Field(
        default=None,
        description="From the `tpm` adapter slot. Always None until that adapter exists.",
    )
    caveats: tuple[str, ...] = Field(
        default_factory=tuple,
        description=(
            "One entry per domain whose adapter was wired in but raised a PlatformError "
            "when called - see docs/HOST_DISCOVERY_ORCHESTRATOR.md#error-propagation. Empty "
            "tuple if every wired adapter succeeded, or none were wired at all. Populating "
            "this field is the orchestrator's job, not this model's own."
        ),
    )


__all__ = ["HostDiscoveryAdapters", "HostDiscoverySnapshot"]
