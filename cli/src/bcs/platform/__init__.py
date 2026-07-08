"""The Platform Layer: BCS's single seam for every OS process execution.

Design: :doc:`/PLATFORM_LAYER` (``docs/PLATFORM_LAYER.md``), accepted per
``docs/decisions/0009-platform-layer-command-runner.md`` (``NFR-008``).

Implemented (Platform-001, Parts 1-4): the immutable result model
(:class:`~bcs.platform.models.CommandResult`, Part 1), the exception
hierarchy (:mod:`bcs.platform.errors`, Part 2), the execution seam
(:mod:`bcs.platform.execution` - :class:`CommandRunner` and
:class:`SubprocessCommandRunner`, Part 3), and dependency injection via
``bcs.context.RuntimeContext.command_runner`` (Part 4).

``adapters/`` (see ``docs/PLATFORM_LAYER.md#how-future-adapters-use-it``)
holds one package per domain, each built on ``CommandRunner``: ``efi``
and ``storage`` are fully implemented; ``secureboot`` has its domain
models, parser, and error hierarchy implemented but no ``adapter.py``
yet; ``mount``/``rsync`` remain undesigned placeholders.

``bcs.inventory.discovery.HostDiscoveryOrchestrator`` calls into the
``efi`` and ``storage`` adapters, wired at ``bcs.app.main()``'s
composition root into ``bcs.context.RuntimeContext.host_discovery_orchestrator``
- see ``docs/HOST_DISCOVERY_ORCHESTRATOR.md``. No CLI command passes
that orchestrator into ``bcs.inventory.service.collect_host_inventory()``
yet.
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
