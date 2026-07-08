"""The Secure Boot Adapter: BCS's read-only Host Discovery adapter for
firmware Secure Boot state.

Design: ``docs/SECURE_BOOT_ADAPTER.md``. Requires no ADR - see
``docs/SECURE_BOOT_ADAPTER.md#adr-recommendation`` - following the same
architecture as ``bcs.platform.adapters.efi`` (see
``docs/decisions/0010-efi-adapter-read-only-scope.md``).

Implemented so far: the immutable domain models
(:mod:`bcs.platform.adapters.secureboot.models`), the error hierarchy
(:mod:`bcs.platform.adapters.secureboot.errors`), and the pure parser
(:mod:`bcs.platform.adapters.secureboot.parser`,
``parse_secure_boot_status(text: str) -> SecureBootStatus`` - not yet
re-exported from this package's own top level; import it directly from
``bcs.platform.adapters.secureboot.parser`` for now). Per the accepted
design, this package will eventually also contain:

- ``adapter.py`` - ``read_secure_boot_status(runner: CommandRunner) ->
  SecureBootStatus``, the only place this package calls
  ``CommandRunner.run()``.

That does not exist yet. Nothing in this package executes a process or
imports ``subprocess``/``CommandRunner`` at this stage.
"""

from bcs.platform.adapters.secureboot.errors import (
    SecureBootError,
    SecureBootParseError,
    SecureBootUnavailableError,
)
from bcs.platform.adapters.secureboot.models import SecureBootState, SecureBootStatus

__all__ = [
    "SecureBootError",
    "SecureBootParseError",
    "SecureBootState",
    "SecureBootStatus",
    "SecureBootUnavailableError",
]
