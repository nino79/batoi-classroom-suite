"""The EFI Adapter: BCS's read-only Host Discovery adapter for firmware
boot configuration.

Design: ``docs/EFI_ADAPTER.md``, accepted per
``docs/decisions/0010-efi-adapter-read-only-scope.md``.

Implemented: the immutable domain models
(:mod:`bcs.platform.adapters.efi.models`), the pure parser
(:mod:`bcs.platform.adapters.efi.parser`), the orchestration adapter
(:mod:`bcs.platform.adapters.efi.adapter`), and the domain-specific
error hierarchy (:mod:`bcs.platform.adapters.efi.errors`).
"""

from bcs.platform.adapters.efi.adapter import read_firmware_boot_configuration
from bcs.platform.adapters.efi.errors import (
    FirmwareBootError,
    FirmwareBootParseError,
    FirmwareBootUnavailableError,
)
from bcs.platform.adapters.efi.models import BootEntry, FirmwareBootConfiguration
from bcs.platform.adapters.efi.parser import parse_firmware_boot_configuration

__all__ = [
    "BootEntry",
    "FirmwareBootConfiguration",
    "FirmwareBootError",
    "FirmwareBootParseError",
    "FirmwareBootUnavailableError",
    "parse_firmware_boot_configuration",
    "read_firmware_boot_configuration",
]
