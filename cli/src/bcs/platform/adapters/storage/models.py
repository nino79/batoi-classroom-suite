"""Immutable domain models for the Storage Adapter.

Design: ``docs/STORAGE_ADAPTER.md#pydantic-models``, reviewed and
accepted as the second Host Discovery adapter (see
``docs/EFI_ADAPTER.md`` and
``docs/decisions/0010-efi-adapter-read-only-scope.md`` for the sibling
adapter this design deliberately mirrors).

This module contains **only the models** - no parsing logic, no
``subprocess``, no :class:`~bcs.platform.execution.CommandRunner`, no
adapter, no CLI integration. Every model here represents an
**observed fact** about the machine's storage topology, exactly as
reported by the underlying tools (``lsblk``, ``blkid``, ``findmnt``);
none of them decides what any fact *means* - e.g. which device is a
suitable deployment target, or which partition "is" the EFI System
Partition, is a decision left to domain services that consume this
adapter's output, per
``docs/STORAGE_ADAPTER.md#adapter-responsibilities``. Validators in
this module check only internal data consistency (a size cannot be
negative, a partition number is 1-based, an identifier cannot appear
twice within the same snapshot) - never a field's consistency with
another field's *meaning* (e.g. whether ``is_nvme`` "should" be
``True`` for a given ``name``), since that would be inference, not
observation.

Naming is domain-driven, not tied to the current backend tools
(``lsblk``/``blkid``/``findmnt``) - see
``docs/standards/naming-conventions.md#domain-driven-naming``.

Field naming mirrors the rest of BCS's models: Python attributes are
``snake_case``, JSON output is ``camelCase`` (``by_alias=True``), and
``populate_by_name=True`` lets callers construct instances with either
spelling. All models are frozen, matching every other model in
``bcs.platform``/``bcs.inventory`` - a point-in-time record, never a
live view.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FilesystemInfo(BaseModel):
    """Filesystem metadata on a partition or whole device, as reported by
    ``blkid``.

    See ``docs/STORAGE_ADAPTER.md#filesysteminfo`` for the authoritative
    field-by-field reference this class implements exactly.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    fs_type: str | None = Field(
        alias="fsType",
        default=None,
        description=(
            "The filesystem type, e.g. 'vfat', 'ext4', 'xfs', 'swap', as reported. None if unknown."
        ),
    )
    uuid: str | None = Field(
        default=None,
        description=(
            "The filesystem UUID, as reported verbatim. None if the "
            "filesystem has none, or it is unknown."
        ),
    )
    label: str | None = Field(
        default=None,
        description="The filesystem label, as reported. None if unset or unknown.",
    )
    mount_options: str | None = Field(
        alias="mountOptions",
        default=None,
        description=(
            "The mount options in effect, e.g. 'rw,relatime'. None if not currently mounted."
        ),
    )
    mount_point: str | None = Field(
        alias="mountPoint",
        default=None,
        description="The current mount point, e.g. '/boot/efi'. None if not currently mounted.",
    )


class Partition(BaseModel):
    """One partition of a block device (e.g. ``/dev/nvme0n1p1``), as
    reported by ``lsblk``/``blkid``.

    See ``docs/STORAGE_ADAPTER.md#partition`` for the authoritative
    field-by-field reference this class implements exactly.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    name: str = Field(
        description="The partition name, without the '/dev/' prefix, e.g. 'nvme0n1p1'."
    )
    path: str = Field(description="The full partition device path, e.g. '/dev/nvme0n1p1'.")
    number: int = Field(ge=1, description="The partition number, 1-based, as reported.")
    size_bytes: int | None = Field(
        alias="sizeBytes",
        default=None,
        ge=0,
        description="The partition size in bytes, or None if unknown.",
    )
    partuuid: str | None = Field(
        default=None,
        description="The GPT partition UUID (PARTUUID), as reported verbatim. None if unknown.",
    )
    parttype: str | None = Field(
        default=None,
        description=(
            "The GPT partition type GUID, as reported verbatim (e.g. "
            "'C12A7328-F81F-11D2-BA4B-00A0C93EC93B' for an EFI System "
            "Partition). This model does not interpret the GUID - "
            "identifying what a given type GUID means is a domain "
            "service's responsibility, not this adapter's."
        ),
    )
    filesystem: FilesystemInfo | None = Field(
        default=None,
        description="Filesystem metadata for this partition, or None if none was reported.",
    )
    mount_point: str | None = Field(
        alias="mountPoint",
        default=None,
        description="The mount point if this partition is mounted, else None.",
    )


class BlockDevice(BaseModel):
    """One whole block device (e.g. ``/dev/nvme0n1``, ``/dev/sda``), as
    reported by ``lsblk``.

    See ``docs/STORAGE_ADAPTER.md#blockdevice`` for the authoritative
    field-by-field reference this class implements exactly.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    name: str = Field(description="The device name, without the '/dev/' prefix, e.g. 'nvme0n1'.")
    path: str = Field(description="The full device path, e.g. '/dev/nvme0n1'.")
    device_type: str = Field(
        alias="deviceType",
        description=(
            "The device type as reported, e.g. 'disk', 'part', 'rom', "
            "'loop', 'raid'. Kept as the tool's own open-ended string "
            "rather than a closed set of known values, since new device "
            "types are a fact of the underlying tool, not something this "
            "model can predict."
        ),
    )
    size_bytes: int | None = Field(
        alias="sizeBytes",
        default=None,
        ge=0,
        description="The device size in bytes, or None if unknown.",
    )
    is_removable: bool = Field(
        alias="isRemovable",
        description="Whether the device is reported as removable (e.g. USB media).",
    )
    is_read_only: bool = Field(
        alias="isReadOnly",
        description="Whether the device is reported as read-only.",
    )
    is_nvme: bool = Field(
        alias="isNvme",
        description="Whether this is an NVMe device, as reported.",
    )
    model: str | None = Field(
        default=None,
        description="The device model string, as reported. None if unknown.",
    )
    vendor: str | None = Field(
        default=None,
        description="The device vendor string, as reported. None if unknown.",
    )
    serial: str | None = Field(
        default=None,
        description="The device serial number, as reported. None if unknown.",
    )
    partitions: tuple[Partition, ...] = Field(
        default_factory=tuple,
        description=(
            "This device's child partitions, in the order reported. Empty for non-disk devices."
        ),
    )
    mount_point: str | None = Field(
        alias="mountPoint",
        default=None,
        description="The mount point if the whole device (not a partition) is mounted, else None.",
    )

    @model_validator(mode="after")
    def _check_partitions_have_unique_numbers(self) -> BlockDevice:
        numbers = [partition.number for partition in self.partitions]
        if len(numbers) != len(set(numbers)):
            msg = "partitions must not contain duplicate number values"
            raise ValueError(msg)
        return self


class MountEntry(BaseModel):
    """One mount point, as reported by ``findmnt``.

    See ``docs/STORAGE_ADAPTER.md#mountentry`` for the authoritative
    field-by-field reference this class implements exactly.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    source: str = Field(
        description=(
            "The mount source, as reported, e.g. a device path, 'UUID=<uuid>', or 'LABEL=<label>'."
        )
    )
    target: str = Field(description="The mount point, e.g. '/boot/efi'.")
    fstype: str = Field(description="The filesystem type, e.g. 'vfat', 'ext4'.")
    options: str = Field(description="The mount options, comma-separated, as reported.")
    parent: str | None = Field(
        default=None,
        description="The parent mount point, for bind mounts. None if this is not a bind mount.",
    )


class StorageConfiguration(BaseModel):
    """The complete storage topology snapshot: every block device and
    every mount point, as reported.

    Deliberately does **not** carry its own ``schemaVersion`` - like
    ``CommandResult`` and ``FirmwareBootConfiguration``, this model is
    never the top-level payload of a ``bcs`` command's own output; it
    is always embedded inside something else's result, so versioning
    is that container's responsibility. See
    ``docs/STORAGE_ADAPTER.md#storageconfiguration`` for the
    authoritative reference this class implements exactly.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    devices: tuple[BlockDevice, ...] = Field(
        default_factory=tuple,
        description="Every block device found (disks and their partitions), in the order reported.",
    )
    mounts: tuple[MountEntry, ...] = Field(
        default_factory=tuple,
        description="Every mount point found, in the order reported.",
    )

    @model_validator(mode="after")
    def _check_devices_have_unique_paths(self) -> StorageConfiguration:
        paths = [device.path for device in self.devices]
        if len(paths) != len(set(paths)):
            msg = "devices must not contain duplicate path values"
            raise ValueError(msg)
        return self


__all__ = [
    "BlockDevice",
    "FilesystemInfo",
    "MountEntry",
    "Partition",
    "StorageConfiguration",
]
