"""Orchestrates the Host Inventory subsystem's collectors into one
immutable :class:`~bcs.inventory.models.HostInventory` snapshot.

This is the one function anything outside ``bcs.inventory`` should
call - ``bcs.commands.inventory`` (the ``bcs inventory`` command) and
``bcs.commands.doctor`` (which evaluates pass/fail checks against the
same facts) both go through here rather than calling individual
collectors directly, so the two never drift apart on how a given fact
is gathered.

**Host Discovery integration**
(``docs/HOST_DISCOVERY_ORCHESTRATOR.md#relationship-to-host-inventory---implemented``,
accepted per ``docs/decisions/0011-host-discovery-orchestrator.md``,
Decision point 7): :func:`collect_host_inventory` accepts an optional
:class:`~bcs.inventory.discovery.orchestrator.HostDiscoveryOrchestrator`.

- **Omitted (the default):** behaviour is byte-for-byte identical to
  before this parameter existed - every field comes from the same nine
  collectors as always.
- **Given:** it is called exactly once (``orchestrator.discover()``).
  Its :class:`~bcs.inventory.discovery.models.HostDiscoverySnapshot`
  supplies ``cpu``/``memory`` when its own ``cpu``/``memory`` fields
  are not ``None`` - a snapshot whose ``cpu``/``memory`` adapter slots
  were never wired, or whose adapter raised a ``PlatformError``,
  reports ``None`` there, and this function falls back to the same
  ``collect_cpu``/``collect_memory`` collector call it would have made
  without an orchestrator at all, rather than passing an invalid
  ``None`` into a required field. This fallback is what makes "preserve
  all existing inventory behaviour" true even for a caller-supplied
  orchestrator with incomplete adapters, not just for the
  no-orchestrator case.
- ``storage`` and ``network`` follow the identical fallback shape as
  ``cpu``/``memory`` (storage: issue #70; network: Beta M3, Network
  Adapter wiring): when ``snapshot.storage_topology``/``snapshot.network``
  is not ``None``, it is translated
  (:func:`_translate_storage_devices`/:func:`_translate_network_interfaces`)
  from the Storage/Network Adapters' richer
  :class:`~bcs.platform.adapters.storage.models.StorageConfiguration`/
  :class:`~bcs.platform.adapters.network.models.NetworkInterfaceStatus`
  into the same ``list[StorageDevice]``/``list[NetworkInterface]`` shape
  ``HostInventory.storage``/``HostInventory.network`` has always had; an
  unset slot, or one whose adapter raised a ``PlatformError`` (leaving
  the snapshot field ``None``), falls back to
  ``collect_storage()``/``collect_network()`` exactly as it would
  without an orchestrator at all.
- Every other section (``identity``, ``firmware``, ``operating_system``,
  ``efi_system_partition``, ``usb_storage``, ``tooling``) is unaffected
  either way - unconditionally sourced from the same collectors,
  whether or not an orchestrator was given.

Per ``docs/decisions/0011-host-discovery-orchestrator.md``'s own
explicit Decision point 6 and Consequences, this does **not** add new
``HostInventory`` fields for the snapshot's other five domains
(``firmware_boot_configuration``/``storage_topology``/``secure_boot``/
``filesystem``/``tpm``) or its ``caveats`` - folding those into this
model's own schema is a separate, not-yet-accepted follow-up (an
ADR-0008 amendment, per that ADR's own Consequences). A caller wanting
that richer data calls ``orchestrator.discover()`` directly; nothing
here re-exposes it.

Any exception ``orchestrator.discover()`` raises propagates out of
this function completely unmodified - no ``try``/``except`` wraps that
call, exactly as none wraps any of the collector calls below. A
``PlatformError`` from a single misbehaving adapter is already isolated
*inside* the orchestrator (recorded as a ``HostDiscoverySnapshot.caveats``
entry, per ``docs/HOST_DISCOVERY_ORCHESTRATOR.md#error-propagation``),
so it never reaches here; anything that does reach here is a genuine,
unexpected bug, not a fact-collection failure to degrade gracefully
from.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from bcs.inventory import collectors
from bcs.inventory.models import HostInventory, NetworkInterface, StorageDevice
from bcs.platform.adapters.network.models import NetworkInterfaceStatus
from bcs.platform.adapters.storage.models import StorageConfiguration

if TYPE_CHECKING:
    from bcs.inventory.discovery.orchestrator import HostDiscoveryOrchestrator


def _translate_storage_devices(config: StorageConfiguration) -> list[StorageDevice]:
    """Translate the Storage Adapter's richer ``StorageConfiguration``
    into the narrower ``list[StorageDevice]`` shape ``HostInventory.storage``
    has always had (see issue #70).

    Only whole-disk devices (``device_type == "disk"``) are translated -
    matching the legacy ``collect_storage()`` collector's own implicit
    scope (its NVMe-only glob could never match a loop/rom/raid device
    name), so this translation does not silently widen what ``bcs
    inventory`` reports beyond what it always has.
    ``BlockDevice.partitions``/``.mounts``/``.device_type``/
    ``.is_removable``/``.is_read_only``/``.vendor``/``.serial`` are not
    carried over - ``StorageDevice`` has no field for any of them, and
    this function is a narrowing translation, not a schema change (see
    ``docs/ISSUE_70_IMPLEMENTATION_CHECKLIST.md`` § 3.1.1).
    """
    return [
        StorageDevice(
            name=device.name,
            path=device.path,
            is_nvme=device.is_nvme,
            size_bytes=device.size_bytes,
            model=device.model,
        )
        for device in config.devices
        if device.device_type == "disk"
    ]


def _translate_network_interfaces(status: NetworkInterfaceStatus) -> list[NetworkInterface]:
    """Translate the Network Adapter's richer ``NetworkInterfaceStatus``
    into the narrower ``list[NetworkInterface]`` shape ``HostInventory.network``
    has always had (Beta M3, Network Adapter wiring).

    A 1:1 field mapping - every interface the Network Adapter reports is
    carried over, in order, including loopback (the legacy
    ``collect_network()`` collector also reports ``lo``, so this
    translation does not narrow *which* interfaces appear, only which
    *fields* of each one). ``NetworkInterfaceStatus.raw_text`` is not
    carried over - ``StorageDevice``-style narrowing, not a schema
    change: ``HostInventory``'s ``NetworkInterface`` has no field for
    it.
    """
    return [
        NetworkInterface(
            name=iface.name,
            mac_address=iface.mac_address,
            ip_addresses=list(iface.ip_addresses),
            is_up=iface.is_up,
            is_loopback=iface.is_loopback,
        )
        for iface in status.interfaces
    ]


def collect_host_inventory(
    orchestrator: HostDiscoveryOrchestrator | None = None,
) -> HostInventory:
    """Collect a fresh, immutable snapshot of the current machine.

    See this module's own docstring for the optional ``orchestrator``
    parameter's exact contract.
    """
    if orchestrator is None:
        cpu = collectors.collect_cpu()
        memory = collectors.collect_memory()
        network = collectors.collect_network()
        storage = collectors.collect_storage()
    else:
        snapshot = orchestrator.discover()
        cpu = snapshot.cpu if snapshot.cpu is not None else collectors.collect_cpu()
        memory = snapshot.memory if snapshot.memory is not None else collectors.collect_memory()
        storage = (
            _translate_storage_devices(snapshot.storage_topology)
            if snapshot.storage_topology is not None
            else collectors.collect_storage()
        )
        network = (
            _translate_network_interfaces(snapshot.network)
            if snapshot.network is not None
            else collectors.collect_network()
        )

    return HostInventory(
        collected_at=datetime.now(UTC),
        identity=collectors.collect_identity(),
        firmware=collectors.collect_firmware(),
        operating_system=collectors.collect_operating_system(),
        cpu=cpu,
        memory=memory,
        efi_system_partition=collectors.collect_efi_system_partition(),
        storage=storage,
        usb_storage=collectors.collect_usb_storage(),
        network=network,
        tooling=collectors.collect_tooling(),
    )


__all__ = ["collect_host_inventory"]
