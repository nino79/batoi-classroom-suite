"""The Platform Layer: BCS's single seam for every OS process execution.

Design: :doc:`/PLATFORM_LAYER` (``docs/PLATFORM_LAYER.md``), accepted per
``docs/decisions/0009-platform-layer-command-runner.md`` (``NFR-008``).

This is **Platform-001, Part 2**: the immutable result model
(:class:`~bcs.platform.models.CommandResult`, Part 1) and the
exception hierarchy (:mod:`bcs.platform.errors`, this part) exist so
far. Per the approved package structure, this package will eventually
also contain:

- ``execution.py`` - ``CommandRunner`` (a structural ``Protocol``) and
  ``SubprocessCommandRunner``, the one module permitted to import
  ``subprocess``.
- ``adapters/`` - one module per external tool (``efibootmgr``,
  ``lsblk``, ``blkid``, ``mount``, ``rsync``), each built on
  ``CommandRunner``.

Neither exists yet. Nothing in this package executes a process or
imports ``subprocess`` at this stage - the exceptions below are never
raised by anything yet; they exist so ``CommandRunner`` has a typed
hierarchy to raise once it is implemented.
"""

from bcs.platform.errors import (
    CommandExecutionError,
    CommandNotFoundError,
    CommandTimeoutError,
    PlatformError,
)
from bcs.platform.models import CommandResult

__all__ = [
    "CommandExecutionError",
    "CommandNotFoundError",
    "CommandResult",
    "CommandTimeoutError",
    "PlatformError",
]
