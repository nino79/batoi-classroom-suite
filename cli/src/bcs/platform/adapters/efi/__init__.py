"""The EFI Adapter: BCS's read-only Host Discovery adapter for firmware
boot configuration.

Design: ``docs/EFI_ADAPTER.md``, accepted per
``docs/decisions/0010-efi-adapter-read-only-scope.md``.

Implemented so far: the immutable domain models
(:mod:`bcs.platform.adapters.efi.models`) and the pure parser
(:mod:`bcs.platform.adapters.efi.parser`). Per the accepted design,
this package will eventually also contain:

- ``adapter.py`` - ``read_firmware_boot_configuration(runner:
  CommandRunner) -> FirmwareBootConfiguration``, the only place this
  package calls ``CommandRunner.run()``.
- ``errors.py`` - ``FirmwareBootError`` and its subclasses.

Neither exists yet. Nothing in this package executes a process or
imports ``subprocess``/``CommandRunner`` at this stage.
"""

from bcs.platform.adapters.efi.models import BootEntry, FirmwareBootConfiguration
from bcs.platform.adapters.efi.parser import parse_firmware_boot_configuration

__all__ = [
    "BootEntry",
    "FirmwareBootConfiguration",
    "parse_firmware_boot_configuration",
]
