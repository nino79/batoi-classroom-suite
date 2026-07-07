"""The Storage Adapter: BCS's read-only Host Discovery adapter for block
storage, partition, and filesystem topology.

Design: ``docs/STORAGE_ADAPTER.md``. Reviewed and accepted as the
second Host Discovery adapter, following the same architecture as
``bcs.platform.adapters.efi`` (see
``docs/decisions/0010-efi-adapter-read-only-scope.md``).

Implemented: the immutable domain models
(:mod:`bcs.platform.adapters.storage.models`), the domain-specific
error hierarchy (:mod:`bcs.platform.adapters.storage.errors`), the pure
parser (:mod:`bcs.platform.adapters.storage.parser`), and the
orchestration adapter (:mod:`bcs.platform.adapters.storage.adapter`) -
the complete adapter as designed in ``docs/STORAGE_ADAPTER.md``.
"""

from bcs.platform.adapters.storage.adapter import read_storage_topology
from bcs.platform.adapters.storage.errors import (
    StorageError,
    StorageParseError,
    StorageUnavailableError,
)
from bcs.platform.adapters.storage.models import (
    BlockDevice,
    FilesystemInfo,
    MountEntry,
    Partition,
    StorageConfiguration,
)
from bcs.platform.adapters.storage.parser import parse_storage_topology

__all__ = [
    "BlockDevice",
    "FilesystemInfo",
    "MountEntry",
    "Partition",
    "StorageConfiguration",
    "StorageError",
    "StorageParseError",
    "StorageUnavailableError",
    "parse_storage_topology",
    "read_storage_topology",
]
