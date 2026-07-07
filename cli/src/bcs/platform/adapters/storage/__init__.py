"""The Storage Adapter: BCS's read-only Host Discovery adapter for block
storage, partition, and filesystem topology.

Design: ``docs/STORAGE_ADAPTER.md``. Reviewed and accepted as the
second Host Discovery adapter, following the same architecture as
``bcs.platform.adapters.efi`` (see
``docs/decisions/0010-efi-adapter-read-only-scope.md``).

Implemented so far: the immutable domain models
(:mod:`bcs.platform.adapters.storage.models`). Per the accepted
design, this package will eventually also contain:

- ``parser.py`` - ``parse_storage_topology(lsblk_output: str,
  blkid_output: str, findmnt_output: str) -> StorageConfiguration``, a
  pure function.
- ``adapter.py`` - ``read_storage_topology(runner: CommandRunner) ->
  StorageConfiguration``, the only place this package calls
  ``CommandRunner.run()``.
- ``errors.py`` - ``StorageError`` and its subclasses.

None of these exist yet. Nothing in this package executes a process or
imports ``subprocess``/``CommandRunner`` at this stage.
"""

from bcs.platform.adapters.storage.models import (
    BlockDevice,
    FilesystemInfo,
    MountEntry,
    Partition,
    StorageConfiguration,
)

__all__ = [
    "BlockDevice",
    "FilesystemInfo",
    "MountEntry",
    "Partition",
    "StorageConfiguration",
]
