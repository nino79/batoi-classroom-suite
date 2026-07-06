"""Immutable data models for the Host Inventory subsystem.

``HostInventory`` is BCS's single source of truth describing the
current machine: firmware, storage, network, operating system, and
tooling facts collected from the host ``bcs`` runs on. It is
deliberately decoupled from any one consumer - Boot Manager, Builder,
and Deploy (once implemented, in Bash per ADR-0004) all consume the
exact same JSON this module produces, and a future REST API or Web UI
can serve or render that same JSON without this module changing at
all. See ``bcs.inventory.service.collect_host_inventory`` for how a
snapshot is built, and ``bcs.commands.inventory`` for the only place
it is ever printed.

Every model here is **frozen**: an inventory snapshot is a point-in-time
observation, not a live view, and must never be mutated after
collection - take a fresh snapshot instead. Frozen Pydantic models are
also hashable *when every field is itself hashable* - true for the
scalar-only models below (``FirmwareInfo``, ``CpuInfo``, ``MemoryInfo``,
``HostIdentity``, ``OperatingSystemInfo``), but not for ``HostInventory``
itself or any model holding a ``list[...]`` field (``storage``,
``network``, ``tooling``), since plain Python lists are never hashable
regardless of immutability elsewhere in the model.

Extensibility mirrors ``bcs.config.models``: the root model (and any
model documented as such) allows ``x-``-prefixed extra keys via
:func:`bcs.model_utils.reject_non_x_extra`, and ``schema_version`` is
this subsystem's own versioning axis - independent of
``bcs-cli/v1alpha1`` (the CLI's own output schema) and ``bcs/v1alpha1``
(ClassroomConfig) - bumped only on a breaking change to this shape.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from bcs.model_utils import reject_non_x_extra

INVENTORY_SCHEMA_VERSION: Final = "bcs-inventory/v1alpha1"


class FrozenModel(BaseModel):
    """Base for inventory models with no extension point: extra keys rejected."""

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)


class FrozenExtensibleModel(BaseModel):
    """Base for inventory models where only ``x-``-prefixed extra keys are allowed."""

    model_config = ConfigDict(frozen=True, extra="allow", populate_by_name=True)

    @model_validator(mode="after")
    def _check_extra(self) -> FrozenExtensibleModel:
        reject_non_x_extra(self)
        return self


class SecureBootState(StrEnum):
    """Firmware Secure Boot state, as observed - see ``PLAT-004``."""

    ENABLED = "enabled"
    DISABLED = "disabled"
    #: Not a UEFI system, or the firmware has no Secure Boot support at all.
    UNSUPPORTED = "unsupported"
    #: A UEFI system whose Secure Boot state could not be determined.
    UNKNOWN = "unknown"


class FirmwareInfo(FrozenModel):
    """UEFI/Secure Boot facts - see ``PLAT-003``, ``PLAT-004``."""

    uefi: bool
    secure_boot: SecureBootState = Field(alias="secureBoot")
    vendor: str | None = None
    version: str | None = None


class StorageDevice(FrozenModel):
    """One block storage device - see ``PLAT-005`` (NVMe as the primary target)."""

    name: str
    path: str
    is_nvme: bool = Field(alias="isNvme")
    size_bytes: int | None = Field(alias="sizeBytes", default=None)
    model: str | None = None


class NetworkInterface(FrozenModel):
    """One network interface, as observed on the host."""

    name: str
    mac_address: str | None = Field(alias="macAddress", default=None)
    ip_addresses: list[str] = Field(alias="ipAddresses", default_factory=list)
    is_up: bool = Field(alias="isUp")
    is_loopback: bool = Field(alias="isLoopback")


class OperatingSystemInfo(FrozenModel):
    """The running operating system - see ``PLAT-001``, ``PLAT-002``."""

    name: str
    version: str | None = None
    kernel: str | None = None
    architecture: str


class MemoryInfo(FrozenModel):
    """System memory, in bytes. Fields are ``None`` where undeterminable."""

    total_bytes: int | None = Field(alias="totalBytes", default=None)
    available_bytes: int | None = Field(alias="availableBytes", default=None)


class CpuInfo(FrozenModel):
    """CPU facts for the host."""

    architecture: str
    model: str | None = None
    logical_cores: int | None = Field(alias="logicalCores", default=None)


class ToolStatus(FrozenModel):
    """Whether one expected external tool (e.g. Clonezilla) is present."""

    name: str
    found: bool
    path: str | None = None


class HostIdentity(FrozenModel):
    """Candidate stable identifiers for this machine.

    Feeds the still-open ``deploy.maintenanceRequests.machineIdentity``
    question from ``docs/CONFIGURATION.md`` and
    ``docs/architecture/deploy.md#open-questions`` - this narrows what
    identity data is *available* on a real host; it does not by itself
    decide the wire format of a Boot Manager maintenance request.
    """

    primary_mac_address: str | None = Field(alias="primaryMacAddress", default=None)
    dmi_product_uuid: str | None = Field(alias="dmiProductUuid", default=None)


class HostInventory(FrozenExtensibleModel):
    """The complete, immutable snapshot: BCS's single source of truth
    describing the current machine.
    """

    schema_version: Literal["bcs-inventory/v1alpha1"] = Field(
        alias="schemaVersion", default=INVENTORY_SCHEMA_VERSION
    )
    collected_at: datetime = Field(alias="collectedAt")
    identity: HostIdentity
    firmware: FirmwareInfo
    operating_system: OperatingSystemInfo = Field(alias="operatingSystem")
    cpu: CpuInfo
    memory: MemoryInfo
    storage: list[StorageDevice] = Field(default_factory=list)
    network: list[NetworkInterface] = Field(default_factory=list)
    tooling: list[ToolStatus] = Field(default_factory=list)


__all__ = [
    "INVENTORY_SCHEMA_VERSION",
    "CpuInfo",
    "FirmwareInfo",
    "FrozenExtensibleModel",
    "FrozenModel",
    "HostIdentity",
    "HostInventory",
    "MemoryInfo",
    "NetworkInterface",
    "OperatingSystemInfo",
    "SecureBootState",
    "StorageDevice",
    "ToolStatus",
]
