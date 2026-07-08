"""The Filesystem Adapter: BCS's read-only Host Discovery adapter for
filesystem usage and capacity.

Design: ``docs/FILESYSTEM_ADAPTER.md``, accepted. Requires no ADR - see
``docs/FILESYSTEM_ADAPTER.md#adr-recommendation`` - following the same
architecture as ``bcs.platform.adapters.efi``/``.storage``/``.secureboot``
(see ``docs/decisions/0010-efi-adapter-read-only-scope.md``).

Implemented: the immutable domain models
(:mod:`bcs.platform.adapters.filesystem.models`), the error hierarchy
(:mod:`bcs.platform.adapters.filesystem.errors`), the pure parser
(:mod:`bcs.platform.adapters.filesystem.parser`), and the orchestration
adapter (:mod:`bcs.platform.adapters.filesystem.adapter`) - the
complete adapter as designed in ``docs/FILESYSTEM_ADAPTER.md``.
"""

from bcs.platform.adapters.filesystem.adapter import read_filesystem_usage
from bcs.platform.adapters.filesystem.errors import (
    FilesystemError,
    FilesystemParseError,
    FilesystemUnavailableError,
)
from bcs.platform.adapters.filesystem.models import FilesystemUsage, FilesystemUsageReport
from bcs.platform.adapters.filesystem.parser import parse_filesystem_usage

__all__ = [
    "FilesystemError",
    "FilesystemParseError",
    "FilesystemUnavailableError",
    "FilesystemUsage",
    "FilesystemUsageReport",
    "parse_filesystem_usage",
    "read_filesystem_usage",
]
