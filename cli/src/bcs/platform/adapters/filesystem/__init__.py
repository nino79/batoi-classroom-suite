"""The Filesystem Adapter: BCS's read-only Host Discovery adapter for
filesystem usage and capacity.

Design: ``docs/FILESYSTEM_ADAPTER.md``, accepted. Requires no ADR - see
``docs/FILESYSTEM_ADAPTER.md#adr-recommendation`` - following the same
architecture as ``bcs.platform.adapters.efi``/``.storage``/``.secureboot``
(see ``docs/decisions/0010-efi-adapter-read-only-scope.md``).

Implemented so far: the immutable domain models
(:mod:`bcs.platform.adapters.filesystem.models`). Per the accepted
design, this package will eventually also contain:

- ``parser.py`` - ``parse_filesystem_usage(text: str) ->
  FilesystemUsageReport``, a pure function.
- ``errors.py`` - ``FilesystemError`` and its two subclasses.
- ``adapter.py`` - ``read_filesystem_usage(runner: CommandRunner) ->
  FilesystemUsageReport``, the only place this package calls
  ``CommandRunner.run()``.

None of those exist yet. Nothing in this package executes a process or
imports ``subprocess``/``CommandRunner`` at this stage.
"""

from bcs.platform.adapters.filesystem.models import FilesystemUsage, FilesystemUsageReport

__all__ = [
    "FilesystemUsage",
    "FilesystemUsageReport",
]
