"""The Network Adapter: BCS's read-only Host Discovery adapter for
network interface status.

Design: ``docs/NETWORK_ADAPTER.md``, accepted. Requires no ADR - see
``docs/NETWORK_ADAPTER.md#adr-recommendation`` - following the same
architecture as ``bcs.platform.adapters.efi``/``.storage``/
``.secureboot``/``.filesystem`` (see
``docs/decisions/0010-efi-adapter-read-only-scope.md``).

Implemented: the immutable domain models
(:mod:`bcs.platform.adapters.network.models`), the error hierarchy
(:mod:`bcs.platform.adapters.network.errors`), the pure parser
(:mod:`bcs.platform.adapters.network.parser`), and the orchestration
adapter (:mod:`bcs.platform.adapters.network.adapter`) - the complete
adapter as designed in ``docs/NETWORK_ADAPTER.md``.
"""

from bcs.platform.adapters.network.adapter import read_network_interfaces
from bcs.platform.adapters.network.errors import (
    NetworkError,
    NetworkParseError,
    NetworkUnavailableError,
)
from bcs.platform.adapters.network.models import NetworkInterface, NetworkInterfaceStatus
from bcs.platform.adapters.network.parser import parse_network_interfaces

__all__ = [
    "NetworkError",
    "NetworkInterface",
    "NetworkInterfaceStatus",
    "NetworkParseError",
    "NetworkUnavailableError",
    "parse_network_interfaces",
    "read_network_interfaces",
]
