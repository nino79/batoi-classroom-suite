"""The Storage Adapter: BCS's read-only Host Discovery adapter for block
storage, partition, and filesystem topology.

Design: ``docs/STORAGE_ADAPTER.md``. Reviewed and accepted as the
second Host Discovery adapter, following the same architecture as
``bcs.platform.adapters.efi`` (see
``docs/decisions/0010-efi-adapter-read-only-scope.md``).

Implemented so far: the immutable domain models
(:mod:`bcs.platform.adapters.storage.models`), the domain-specific
error hierarchy (:mod:`bcs.platform.adapters.storage.errors`), and the
pure parser (:mod:`bcs.platform.adapters.storage.parser`). Per the
accepted design, this package will eventually also contain:

- ``adapter.py`` - ``read_storage_topology(runner: CommandRunner) ->
  StorageConfiguration``, the only place this package calls
  ``CommandRunner.run()``.

Nothing in this package executes a process or imports
``subprocess``/``CommandRunner`` at this stage.
"""

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
]
