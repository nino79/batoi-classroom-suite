"""Immutable domain models for the Network Adapter.

Design: ``docs/NETWORK_ADAPTER.md#domain-models``. This design requires
no ADR (see ``docs/NETWORK_ADAPTER.md#adr-recommendation``) - every
architectural mechanism it uses was already decided by
``docs/decisions/0008-host-inventory-ports-and-adapters.md``,
``docs/decisions/0009-platform-layer-command-runner.md``,
``docs/decisions/0010-efi-adapter-read-only-scope.md``, and
``docs/decisions/0011-host-discovery-orchestrator.md``.

This module contains **only the models** - no parsing logic, no
``subprocess``, no :class:`~bcs.platform.execution.CommandRunner`, no
adapter, no CLI integration. ``NetworkInterface``/``NetworkInterfaceStatus``
represent **observed facts** about currently visible network
interfaces, exactly as reported by the underlying tool (``ip``); neither
decides which interface is "primary," "management," or "deployment" -
those are decisions left to domain services that consume this adapter's
output, per ``docs/NETWORK_ADAPTER.md#scope-guarantee``.

**Independently defined, not imported from ``bcs.inventory.models``:**
``bcs.inventory.models.NetworkInterface`` already exists at the Host
Inventory layer, but importing it here would create a dependency from
``bcs.platform`` (a lower layer) up into ``bcs.inventory`` (a higher
layer) - the same architectural inversion
``docs/SECURE_BOOT_ADAPTER.md#naming-rationale`` already ruled out for
``SecureBootState``. This module's ``NetworkInterface`` is therefore an
independently defined model with the same name and compatible fields -
see ``docs/NETWORK_ADAPTER.md#naming-rationale``.

Naming is domain-driven, not tied to the current backend tool (``ip``)
- see ``docs/standards/naming-conventions.md#domain-driven-naming``.
``NetworkInterfaceStatus`` follows the ``<Domain>Status`` pattern
``SecureBootStatus`` already established: "observed condition, not a
configurable state" - see ``docs/NETWORK_ADAPTER.md#domain-models``.

Field naming mirrors the rest of BCS's models: Python attributes are
``snake_case``, JSON output is ``camelCase`` (``by_alias=True``), and
``populate_by_name=True`` lets callers construct instances with either
spelling. Both models are frozen, matching every other model in
``bcs.platform`` - a point-in-time record, never a live view. Neither
carries its own ``schemaVersion``, for the same reason none of the
sibling adapters' top-level models do: neither is ever a ``bcs``
command's own top-level payload.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class NetworkInterface(BaseModel):
    """One observed network interface, as reported by ``ip -json addr
    show``.

    See ``docs/NETWORK_ADAPTER.md#domain-models`` for the authoritative
    field-by-field reference this class implements exactly.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    name: str = Field(description=("The interface name as reported, e.g. 'eth0', 'lo', 'wlp2s0'."))
    mac_address: str | None = Field(
        alias="macAddress",
        default=None,
        description=(
            "The link-layer address as reported, e.g. "
            "'52:54:00:12:34:56'. None for interfaces that have no MAC "
            "address in their ip -json output (loopback, tun/tap), and "
            "also normalised to None for the null MAC "
            "(00:00:00:00:00:00) - see "
            "docs/NETWORK_ADAPTER.md#open-questions."
        ),
    )
    ip_addresses: tuple[str, ...] = Field(
        alias="ipAddresses",
        default_factory=tuple,
        description=(
            "All IP addresses currently assigned to this interface "
            "(IPv4 and IPv6, including link-local), in the order "
            "reported. Empty tuple if no address is assigned."
        ),
    )
    is_up: bool = Field(
        alias="isUp",
        description=(
            "Whether the interface is administratively UP and has "
            "carrier (LOWER_UP flag present in the flags array)."
        ),
    )
    is_loopback: bool = Field(
        alias="isLoopback",
        description=("Whether the interface has the LOOPBACK flag set in its flags array."),
    )


class NetworkInterfaceStatus(BaseModel):
    """The complete network interface snapshot: every interface ``ip
    -json addr show`` reported, plus the verbatim source text.

    See ``docs/NETWORK_ADAPTER.md#domain-models`` for the authoritative
    field-by-field reference this class implements exactly.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    interfaces: tuple[NetworkInterface, ...] = Field(
        default_factory=tuple,
        description=(
            "Every network interface found, in the order the kernel "
            "reported them. Empty tuple if no interfaces exist "
            "(defensive; not expected on a deployed system)."
        ),
    )
    raw_text: str = Field(
        alias="rawText",
        description=(
            "The complete, unparsed source text, verbatim - the same "
            "audit/debugging rationale FirmwareBootConfiguration.raw_text/"
            "SecureBootStatus.raw_text/FilesystemUsageReport.raw_text "
            "already established."
        ),
    )


__all__ = ["NetworkInterface", "NetworkInterfaceStatus"]
