"""The EFI Adapter: BCS's read-only Host Discovery adapter for firmware
boot configuration.

Design: ``docs/EFI_ADAPTER.md``, accepted per
``docs/decisions/0010-efi-adapter-read-only-scope.md``.

This is **Host Discovery, models only**: only the immutable domain
models (:mod:`bcs.platform.adapters.efi.models`) exist so far. Per the
accepted design, this package will eventually also contain:

- ``parser.py`` - ``parse_firmware_boot_configuration(text: str) ->
  FirmwareBootConfiguration``, a pure function independent of the
  execution layer.
- ``adapter.py`` - ``read_firmware_boot_configuration(runner:
  CommandRunner) -> FirmwareBootConfiguration``, the only place this
  package calls ``CommandRunner.run()``.
- ``errors.py`` - ``FirmwareBootError`` and its subclasses.

None of those exist yet. Nothing in this package parses text, executes
a process, or imports ``subprocess``/``CommandRunner`` at this stage.
"""

from bcs.platform.adapters.efi.models import BootEntry, FirmwareBootConfiguration

__all__ = ["BootEntry", "FirmwareBootConfiguration"]
