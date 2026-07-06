"""The Platform Layer: BCS's single seam for every OS process execution.

Design: :doc:`/PLATFORM_LAYER` (``docs/PLATFORM_LAYER.md``), accepted per
``docs/decisions/0009-platform-layer-command-runner.md`` (``NFR-008``).

This is **Platform-001, Part 3**: the immutable result model
(:class:`~bcs.platform.models.CommandResult`, Part 1), the exception
hierarchy (:mod:`bcs.platform.errors`, Part 2), and the execution seam
(:mod:`bcs.platform.execution`, this part - :class:`CommandRunner` and
:class:`SubprocessCommandRunner`) exist so far.

Not yet implemented:

- Integration with ``bcs.context.RuntimeContext`` (no
  ``command_runner`` field yet - every command/collector still has to
  construct its own :class:`~bcs.platform.execution.SubprocessCommandRunner`
  explicitly).
- ``adapters/`` - one module per external tool (``efibootmgr``,
  ``lsblk``, ``blkid``, ``mount``, ``rsync``), each built on
  ``CommandRunner``.

Nothing in ``bcs.inventory``, ``bcs.commands``, or anywhere else in
``cli/`` calls into this package yet.
"""

from bcs.platform.errors import (
    CommandExecutionError,
    CommandNotFoundError,
    CommandTimeoutError,
    PlatformError,
)
from bcs.platform.execution import CommandRunner, SubprocessCommandRunner
from bcs.platform.models import CommandResult

__all__ = [
    "CommandExecutionError",
    "CommandNotFoundError",
    "CommandResult",
    "CommandRunner",
    "CommandTimeoutError",
    "PlatformError",
    "SubprocessCommandRunner",
]
