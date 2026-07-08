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

**A documented correction to the design document's own field table**:
``HostDiscoveryAdapters.network`` is typed
``Callable[[], list[NetworkInterface]]``, matching
``bcs.inventory.collectors.collect_network``'s actual return type
(``list[NetworkInterface]``, per ``bcs.inventory.models.HostInventory``)
rather than the ``tuple[NetworkInterface, ...]`` the design document's
own Public API table used - a real, self-identified inconsistency
(this project's own architecture review of that document, finding 6)
that would otherwise make the design's own "no binding needed" claim
for that slot false under ``mypy --strict``. ``HostDiscoverySnapshot.network``
keeps ``tuple[NetworkInterface, ...]``, since the *snapshot* (unlike
the DI bundle) must stay immutable; converting ``list`` to ``tuple`` is
the orchestrator's job, once it exists.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

from bcs.inventory.models import CpuInfo, MemoryInfo, NetworkInterface
from bcs.platform.adapters.efi.models import FirmwareBootConfiguration
from bcs.platform.adapters.secureboot.models import SecureBootStatus
from bcs.platform.adapters.storage.models import StorageConfiguration


@dataclass(frozen=True)
class HostDiscoveryAdapters:
    """A dependency-injection bundle of already-bound, zero-argument
    Discovery adapter callables - one named slot per domain.

    Every field is **optional** and defaults to ``None``, meaning "no
    adapter wired in for this domain in this build" - never an error by
    itself. Fields for domains with an accepted, implemented adapter
    (``efi``, ``storage``, ``secure_boot``) are typed against that
    adapter's own return model; fields for domains with no accepted
    adapter design yet (``filesystem``, ``tpm``) are typed
    ``Callable[[], object] | None`` - deliberately generic, since there
    is no concrete model to reference yet. ``network``/``cpu``/``memory``
    reuse the existing, already-implemented ``bcs.inventory.collectors``
    functions as-is (``collect_network``/``collect_cpu``/``collect_memory``
    are already zero-argument and satisfy these slots' types directly -
    no binding needed).

    Not a Pydantic model: this bundle holds callables, not serializable
    data. A frozen ``dataclass`` mirrors ``bcs.context.RuntimeContext``'s
    own precedent exactly - a frozen bundle of collaborators, built once
    at the composition root.
    """

    efi: Callable[[], FirmwareBootConfiguration] | None = None
    storage: Callable[[], StorageConfiguration] | None = None
    secure_boot: Callable[[], SecureBootStatus] | None = None
    filesystem: Callable[[], object] | None = None
    network: Callable[[], list[NetworkInterface]] | None = None
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

    **Hashable where every field's actual value is hashable** - not
    unconditionally, the same caveat ``bcs.inventory.models`` already
    documents for itself: every field here is either a frozen model
    with only hashable fields, ``None``, an ``object``-typed opaque
    value, or a tuple - except ``network``, whose ``NetworkInterface``
    elements carry their own ``ip_addresses: list[str]`` field. Because
    a plain ``list`` is never hashable *by type*, independent of
    whether it happens to be empty, **any** ``HostDiscoverySnapshot``
    whose ``network`` tuple contains at least one ``NetworkInterface``
    is unhashable - only a snapshot with an *empty* ``network`` tuple
    hashes without error. This is the same reason ``HostInventory``
    itself is not unconditionally hashable.
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
    filesystem: object | None = Field(
        default=None,
        description="From the `filesystem` adapter slot. Always None until that adapter exists.",
    )
    network: tuple[NetworkInterface, ...] = Field(
        default_factory=tuple,
        description="From the `network` adapter slot. Empty tuple if unset.",
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
