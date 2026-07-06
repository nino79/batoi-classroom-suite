"""The Platform Layer: BCS's single seam for every OS process execution.

Design: :doc:`/PLATFORM_LAYER` (``docs/PLATFORM_LAYER.md``), accepted per
``docs/decisions/0009-platform-layer-command-runner.md`` (``NFR-008``).

This is **Platform-001, Part 1**: only the immutable result model
(:class:`~bcs.platform.models.CommandResult`) exists so far. Per the
approved package structure, this package will eventually also contain:

- ``execution.py`` - ``CommandRunner`` (a structural ``Protocol``) and
  ``SubprocessCommandRunner``, the one module permitted to import
  ``subprocess``.
- ``errors.py`` - the ``PlatformError`` exception hierarchy.
- ``adapters/`` - one module per external tool (``efibootmgr``,
  ``lsblk``, ``blkid``, ``mount``, ``rsync``), each built on
  ``CommandRunner``.

None of those exist yet. Nothing in this package executes a process or
imports ``subprocess`` at this stage.
"""

from bcs.platform.models import CommandResult

__all__ = ["CommandResult"]
