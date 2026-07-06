"""Orchestrates the Host Inventory subsystem's collectors into one
immutable :class:`~bcs.inventory.models.HostInventory` snapshot.

This is the one function anything outside ``bcs.inventory`` should
call - ``bcs.commands.inventory`` (the ``bcs inventory`` command) and
``bcs.commands.doctor`` (which evaluates pass/fail checks against the
same facts) both go through here rather than calling individual
collectors directly, so the two never drift apart on how a given fact
is gathered.
"""

from __future__ import annotations

from datetime import UTC, datetime

from bcs.inventory import collectors
from bcs.inventory.models import HostInventory


def collect_host_inventory() -> HostInventory:
    """Collect a fresh, immutable snapshot of the current machine."""
    return HostInventory(
        collected_at=datetime.now(UTC),
        identity=collectors.collect_identity(),
        firmware=collectors.collect_firmware(),
        operating_system=collectors.collect_operating_system(),
        cpu=collectors.collect_cpu(),
        memory=collectors.collect_memory(),
        efi_system_partition=collectors.collect_efi_system_partition(),
        storage=collectors.collect_storage(),
        usb_storage=collectors.collect_usb_storage(),
        network=collectors.collect_network(),
        tooling=collectors.collect_tooling(),
    )


__all__ = ["collect_host_inventory"]
