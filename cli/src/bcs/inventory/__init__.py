"""The Host Inventory subsystem: BCS's single source of truth
describing the current machine.

- :mod:`bcs.inventory.models` - immutable Pydantic models, the schema.
- :mod:`bcs.inventory.collectors` - stdlib-only probes, one per fact.
- :mod:`bcs.inventory.service` - :func:`collect_host_inventory`, the
  one entry point that assembles a full snapshot.

Nothing in this package prints; see ``bcs.commands.inventory`` for the
only place a snapshot is rendered.
"""

from bcs.inventory.models import HostInventory
from bcs.inventory.service import collect_host_inventory

__all__ = ["HostInventory", "collect_host_inventory"]
