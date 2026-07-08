"""The Secure Boot Adapter: BCS's read-only Host Discovery adapter for
firmware Secure Boot state.

Design: ``docs/SECURE_BOOT_ADAPTER.md``, accepted. Requires no ADR -
see ``docs/SECURE_BOOT_ADAPTER.md#adr-recommendation`` - following the
same architecture as ``bcs.platform.adapters.efi`` (see
``docs/decisions/0010-efi-adapter-read-only-scope.md``).

Implemented: the immutable domain models
(:mod:`bcs.platform.adapters.secureboot.models`), the error hierarchy
(:mod:`bcs.platform.adapters.secureboot.errors`), the pure parser
(:mod:`bcs.platform.adapters.secureboot.parser`), and the orchestration
adapter (:mod:`bcs.platform.adapters.secureboot.adapter`) - the
complete adapter as designed in ``docs/SECURE_BOOT_ADAPTER.md``.
"""

from bcs.platform.adapters.secureboot.adapter import read_secure_boot_status
from bcs.platform.adapters.secureboot.errors import (
    SecureBootError,
    SecureBootParseError,
    SecureBootUnavailableError,
)
from bcs.platform.adapters.secureboot.models import SecureBootState, SecureBootStatus
from bcs.platform.adapters.secureboot.parser import parse_secure_boot_status

__all__ = [
    "SecureBootError",
    "SecureBootParseError",
    "SecureBootState",
    "SecureBootStatus",
    "SecureBootUnavailableError",
    "parse_secure_boot_status",
    "read_secure_boot_status",
]
