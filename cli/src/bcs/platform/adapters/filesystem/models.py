"""Immutable domain models for the Filesystem Adapter.

Design: ``docs/FILESYSTEM_ADAPTER.md#domain-models``. This design
requires no ADR (see ``docs/FILESYSTEM_ADAPTER.md#adr-recommendation``)
- every architectural mechanism it uses was already decided by
``docs/decisions/0008-host-inventory-ports-and-adapters.md``,
``docs/decisions/0009-platform-layer-command-runner.md``,
``docs/decisions/0010-efi-adapter-read-only-scope.md``, and
``docs/decisions/0011-host-discovery-orchestrator.md``.

This module contains **only the models** - no parsing logic, no
``subprocess``, no :class:`~bcs.platform.execution.CommandRunner`, no
adapter, no CLI integration. ``FilesystemUsage``/``FilesystemUsageReport``
represent **observed facts** about currently mounted filesystems,
exactly as reported by the underlying tool (``df``); neither decides
whether a filesystem has "enough" free space, is "healthy," or is "the"
deployment target - those are decisions left to domain services that
consume this adapter's output, per
``docs/FILESYSTEM_ADAPTER.md#scope-guarantee``. Validation in this
module checks only intrinsic data-type consistency (a byte or inode
count cannot be negative) - never a field's consistency with another
field's *meaning* (e.g. ``used_bytes + available_bytes == size_bytes``,
which reserved filesystem blocks routinely make untrue for perfectly
healthy filesystems - see ``docs/FILESYSTEM_ADAPTER.md#domain-models``),
and never a rejection of a legitimately observed, if unusual, machine
state: ``FilesystemUsageReport`` deliberately does **not** reject two
entries sharing the same ``target`` - mount stacking (overmounting) is
a real condition, not a data error, and rejecting or silently
deduplicating it would violate this adapter's "expose facts, never
hide them" mandate.

Naming is domain-driven, not tied to the current backend tool (``df``)
- see ``docs/standards/naming-conventions.md#domain-driven-naming``:
``FilesystemUsage``/``FilesystemUsageReport``, not ``DfOutput`` or
similar - see ``docs/FILESYSTEM_ADAPTER.md#package-structure`` for the
full naming rationale.

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


class FilesystemUsage(BaseModel):
    """Usage and capacity facts for one currently mounted filesystem, as
    reported by ``df``.

    See ``docs/FILESYSTEM_ADAPTER.md#domain-models`` for the
    authoritative field-by-field reference this class implements
    exactly.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    source: str = Field(
        description=(
            "The mount source as df reports it - a device path "
            "('/dev/nvme0n1p2'), a pseudo-source ('tmpfs'), or a network "
            "source. Kept opaque and verbatim; this model does not resolve "
            "it to a StorageConfiguration device - see "
            "docs/FILESYSTEM_ADAPTER.md#relationship-to-the-storage-adapter."
        )
    )
    target: str = Field(
        description=(
            "The mount point, e.g. '/', '/boot/efi', '/home'. May "
            "legitimately contain internal whitespace (e.g. a USB drive "
            "auto-mounted under a label with a space)."
        )
    )
    fs_type: str = Field(
        alias="fsType",
        description=(
            "The filesystem type as reported, e.g. 'ext4', 'vfat', "
            "'tmpfs', 'overlay'. Kept as df's own open-ended string, "
            "mirroring BlockDevice.device_type's identical 'tool's own "
            "string, not a closed enum' reasoning."
        ),
    )
    size_bytes: int = Field(
        alias="sizeBytes",
        ge=0,
        description="Total filesystem size, in bytes.",
    )
    used_bytes: int = Field(
        alias="usedBytes",
        ge=0,
        description="Used space, in bytes.",
    )
    available_bytes: int = Field(
        alias="availableBytes",
        ge=0,
        description=(
            "Space available to an unprivileged writer, in bytes - df's "
            "own 'avail' figure, which already accounts for any "
            "filesystem-reserved blocks (e.g. ext4's default 5% root "
            "reservation). Deliberately not required to satisfy "
            "used_bytes + available_bytes == size_bytes - reserved "
            "blocks routinely make that arithmetic not hold for "
            "perfectly healthy, real filesystems."
        ),
    )
    inodes_total: int | None = Field(
        alias="inodesTotal",
        default=None,
        ge=0,
        description=(
            "Total inode count, or None if df -i-equivalent reporting is "
            "not meaningful for this filesystem type (df itself reports "
            "'-' for these on filesystems with no fixed inode allocation, "
            "e.g. many vfat/network filesystems) - a normal, expected "
            "condition, never an error."
        ),
    )
    inodes_used: int | None = Field(
        alias="inodesUsed",
        default=None,
        ge=0,
        description="Used inode count, or None - see inodes_total.",
    )
    inodes_available: int | None = Field(
        alias="inodesAvailable",
        default=None,
        ge=0,
        description="Available inode count, or None - see inodes_total.",
    )
    raw_line: str = Field(
        alias="rawLine",
        description=(
            "This entry's complete original df output line, verbatim - "
            "the per-entry equivalent of FilesystemUsageReport.raw_text, "
            "so nothing the parser's column-splitting logic might get "
            "subtly wrong is ever silently unrecoverable."
        ),
    )


class FilesystemUsageReport(BaseModel):
    """The complete filesystem usage snapshot: every currently mounted
    filesystem ``df`` reported, plus the verbatim source text.

    See ``docs/FILESYSTEM_ADAPTER.md#domain-models`` for the
    authoritative field-by-field reference this class implements
    exactly.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    filesystems: tuple[FilesystemUsage, ...] = Field(
        default_factory=tuple,
        description=(
            "Every filesystem df reported, in the order df presented "
            "them. Empty tuple if df reported none. May legitimately "
            "contain more than one entry for the same target (mount "
            "stacking) - this model never deduplicates or rejects what "
            "df actually reported."
        ),
    )
    raw_text: str = Field(
        alias="rawText",
        description=(
            "The complete, unparsed stdout text, verbatim - the same "
            "audit/debugging rationale FirmwareBootConfiguration.raw_text/"
            "SecureBootStatus.raw_text already established."
        ),
    )
    raw_stderr: str = Field(
        alias="rawStderr",
        default="",
        description=(
            "The complete, unparsed stderr text, verbatim - empty string "
            "if df wrote nothing to stderr. This is the mechanism that "
            "keeps a partial df failure observable rather than silently "
            "discarded - see "
            "docs/FILESYSTEM_ADAPTER.md#adapter-responsibilities and "
            "docs/FILESYSTEM_ADAPTER.md#relationship-to-the-host-"
            "discovery-orchestrators-caveats-model. "
            "parse_filesystem_usage itself always leaves this at its "
            "default ('') - the parser only ever sees stdout; it is "
            "adapter.py's job to attach the real value before returning."
        ),
    )


__all__ = ["FilesystemUsage", "FilesystemUsageReport"]
