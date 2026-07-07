"""The Storage Adapter's pure parser.

Design: ``docs/STORAGE_ADAPTER.md#parser-architecture``, accepted as
the second Host Discovery adapter (see
``docs/decisions/0010-efi-adapter-read-only-scope.md`` for the sibling
adapter this module's independence guarantees mirror exactly).

:func:`parse_storage_topology` is a **pure function**, with the same
independence guarantees already established for the EFI Adapter's
parser (``bcs.platform.adapters.efi.parser``):

- It accepts only ``str`` text - three of them, one per tool (see
  below) - never a captured process result object.
- It produces only immutable Pydantic models
  (:mod:`bcs.platform.adapters.storage.models`).
- It never imports ``subprocess``, ``CommandRunner``,
  ``bcs.platform.execution``, Typer, or Rich, and performs no
  filesystem access - there is no code path by which this module could
  execute anything, print anything, or read anything beyond the three
  strings it is given.
- It never knows where its input text came from - a live tool
  invocation, a fixture file, a value typed at a REPL. Nothing here
  assumes a specific provenance.
- It never imports the Platform Layer's ``PlatformError`` hierarchy
  (:mod:`bcs.platform.adapters.storage.errors`). Like the EFI parser,
  this module raises only :class:`ValueError` (malformed structure) and
  lets ``pydantic.ValidationError`` propagate (a model-level invariant
  violated). Translating either into ``StorageParseError`` is
  ``adapter.py``'s job, not this module's - see
  ``bcs.platform.adapters.efi.adapter`` for the pattern this adapter is
  expected to follow once it exists.

Three-input composition (``docs/STORAGE_ADAPTER.md#design-decision-three-tool-composition``):
``lsblk -J -b`` gives device-tree structure, ``blkid -p -o json`` gives
per-partition filesystem/GPT metadata, and ``findmnt -J`` gives mount
topology - three tools with distinct output semantics, composed here
rather than each parsed by a separate public function, so a caller
gets one immutable :class:`~bcs.platform.adapters.storage.models.StorageConfiguration`
from one call.

Parsing philosophy: **normalize and merge observed facts only.** This
module builds the device tree from ``lsblk``, annotates it with
``blkid``'s per-partition facts, and cross-references ``findmnt``'s
mount table onto it - matching path strings and copying fields
verbatim. It never decides which device or partition is a "primary"
disk, a "system" disk, an installation target, the EFI System
Partition, a "boot" disk, or an operating-system disk; nothing here
inspects ``parttype`` GUIDs, filesystem types, or mount points to make
such a judgment. That judgment, if it is ever made, belongs to a
domain service consuming this adapter's output - see
``docs/STORAGE_ADAPTER.md#partition-type-guid``.

**Documented assumptions about the JSON shapes**, since none of these
three tools' exact key names are pinned as a hard fact by
``docs/STORAGE_ADAPTER.md`` (the same category of "confirm empirically
before implementation" caveat ``docs/EFI_ADAPTER.md`` already applied
to its own backend tool's exact version behaviour):

- ``lsblk -J -b`` and ``blkid -o json`` are both assumed to wrap their
  entries in a top-level ``"blockdevices"`` array (the shared
  ``libsmartcols``-based JSON convention modern util-linux uses across
  its tools). Each entry's device/partition identifier is the bare
  ``"name"`` for ``lsblk`` (this parser derives the ``/dev/``-prefixed
  path itself) and the full ``"name"`` device path for ``blkid``.
- ``lsblk`` entries are assumed to carry ``"type"``, ``"ro"``, ``"rm"``,
  optionally ``"size"``/``"model"``/``"vendor"``/``"serial"``/``"partn"``,
  and either a legacy singular ``"mountpoint"`` or a newer
  ``"mountpoints"`` array (a real, documented util-linux behaviour
  change across versions, handled here deliberately - not a
  speculative fallback). A partition's 1-based ``number`` is taken from
  ``"partn"`` when present, else derived from its position within its
  parent's ``"children"`` array.
- ``blkid`` entries are assumed to carry ``"type"`` (filesystem type),
  ``"uuid"``, ``"label"``, ``"partuuid"``, and ``"parttype"`` - note
  that ``lsblk``'s ``"type"`` (device type, e.g. ``"disk"``/``"part"``)
  and ``blkid``'s ``"type"`` (filesystem type) are unrelated fields
  that happen to share a JSON key name in their respective tools; this
  module never confuses the two, since each is read from its own
  tool's entries only.
- ``findmnt -J`` is assumed to wrap its entries in a top-level
  ``"filesystems"`` array, each carrying ``"target"``, ``"source"``,
  ``"fstype"``, ``"options"``, and an optional nested ``"children"``
  array for bind mounts - this is well-established, long-standing
  ``findmnt`` behaviour, not a guess.

Real captured fixtures will confirm or correct these assumptions once
they exist (see ``cli/tests/fixtures/storage/README.md``); until then,
this parser is tested against a synthetic corpus built to this
documented shape, exactly as the EFI parser was before real
``efibootmgr`` captures existed.
"""

from __future__ import annotations

import json
from typing import Any, NamedTuple

from bcs.platform.adapters.storage.models import (
    BlockDevice,
    FilesystemInfo,
    MountEntry,
    Partition,
    StorageConfiguration,
)


class _BlkidFacts(NamedTuple):
    """Per-device facts extracted from one ``blkid`` JSON entry.

    Purely a parsing-internal scratch structure - never exposed outside
    this module, not a domain model in its own right.
    """

    fs_type: str | None
    uuid: str | None
    label: str | None
    partuuid: str | None
    parttype: str | None

    @property
    def has_filesystem_data(self) -> bool:
        return self.fs_type is not None or self.uuid is not None or self.label is not None


def parse_storage_topology(
    lsblk_output: str,
    blkid_output: str,
    findmnt_output: str,
) -> StorageConfiguration:
    """Parse the three tools' raw text output into a
    :class:`~bcs.platform.adapters.storage.models.StorageConfiguration`.

    Args:
        lsblk_output: The complete, verbatim stdout of ``lsblk -J -b``.
        blkid_output: The complete, verbatim stdout of ``blkid -p -o json``.
        findmnt_output: The complete, verbatim stdout of ``findmnt -J``.

    Returns:
        A :class:`StorageConfiguration` with every device/partition
        ``lsblk`` reported, annotated with ``blkid``'s per-partition
        filesystem and GPT facts and ``findmnt``'s mount points, plus
        the complete, flat list of mount entries ``findmnt`` reported
        (including mounts with no corresponding block device, e.g.
        ``tmpfs``/``proc`` - those are real facts too, just not part of
        the device tree).

    Raises:
        ValueError: Any of the three inputs is not valid JSON, is
            missing its expected top-level array, or an entry is
            missing a field this parser cannot proceed without (e.g.
            a device with no ``name``). The message names the tool and
            the specific problem.
        pydantic.ValidationError: The assembled data violates a model
            invariant this function cannot check while merging (e.g.
            two devices sharing the same ``path``, or two partitions
            of the same device sharing the same ``number`` - see
            :meth:`StorageConfiguration._check_devices_have_unique_paths`
            and :meth:`BlockDevice._check_partitions_have_unique_numbers`).
    """
    devices = _parse_lsblk(lsblk_output)
    blkid_facts = _parse_blkid(blkid_output)
    devices = [_annotate_device_with_blkid(device, blkid_facts) for device in devices]
    mounts = _parse_findmnt(findmnt_output)
    devices = [_annotate_device_with_mounts(device, mounts) for device in devices]
    return StorageConfiguration(devices=tuple(devices), mounts=mounts)


# ---------------------------------------------------------------------------
# lsblk -J -b -> device tree
# ---------------------------------------------------------------------------


def _parse_lsblk(text: str) -> list[BlockDevice]:
    root = _load_json(text, tool="lsblk")
    raw_devices = _require_list(root, "blockdevices", tool="lsblk")
    return [_parse_block_device(entry) for entry in raw_devices]


def _parse_block_device(entry: dict[str, Any]) -> BlockDevice:
    name = _require_str(entry, "name", tool="lsblk")
    device_type = _require_str(entry, "type", tool="lsblk", context=name)
    is_read_only = _require_bool(entry, "ro", tool="lsblk", context=name)
    is_removable = _require_bool(entry, "rm", tool="lsblk", context=name)
    raw_children = entry.get("children", [])
    if not isinstance(raw_children, list):
        msg = f"lsblk: device {name!r} has a non-list 'children' value"
        raise ValueError(msg)
    partitions = tuple(
        _parse_partition(child, fallback_number=index)
        for index, child in enumerate(raw_children, start=1)
    )
    return BlockDevice(
        name=name,
        path=f"/dev/{name}",
        device_type=device_type,
        size_bytes=entry.get("size"),
        is_removable=is_removable,
        is_read_only=is_read_only,
        is_nvme=name.startswith("nvme"),
        model=entry.get("model"),
        vendor=entry.get("vendor"),
        serial=entry.get("serial"),
        partitions=partitions,
        mount_point=_extract_mount_point(entry),
    )


def _parse_partition(entry: dict[str, Any], *, fallback_number: int) -> Partition:
    name = _require_str(entry, "name", tool="lsblk")
    partn = entry.get("partn")
    number = partn if isinstance(partn, int) and not isinstance(partn, bool) else fallback_number
    return Partition(
        name=name,
        path=f"/dev/{name}",
        number=number,
        size_bytes=entry.get("size"),
        mount_point=_extract_mount_point(entry),
    )


def _extract_mount_point(entry: dict[str, Any]) -> str | None:
    """Handle both the legacy singular ``mountpoint`` key and the newer
    util-linux ``mountpoints`` array key - a real, documented ``lsblk``
    behaviour change across versions, not a speculative fallback. Only
    the first non-null mount point is used; a device mounted at several
    points simultaneously is out of scope for this single-value field.
    """
    mountpoints = entry.get("mountpoints")
    if isinstance(mountpoints, list):
        for point in mountpoints:
            if point:
                return str(point)
        return None
    single = entry.get("mountpoint")
    return str(single) if single else None


# ---------------------------------------------------------------------------
# blkid -p -o json -> per-partition annotations
# ---------------------------------------------------------------------------


def _parse_blkid(text: str) -> dict[str, _BlkidFacts]:
    root = _load_json(text, tool="blkid")
    raw_entries = _require_list(root, "blockdevices", tool="blkid")
    facts: dict[str, _BlkidFacts] = {}
    for entry in raw_entries:
        name = _require_str(entry, "name", tool="blkid")
        facts[name] = _BlkidFacts(
            fs_type=_optional_str(entry, "type"),
            uuid=_optional_str(entry, "uuid"),
            label=_optional_str(entry, "label"),
            partuuid=_optional_str(entry, "partuuid"),
            parttype=_optional_str(entry, "parttype"),
        )
    return facts


def _optional_str(entry: dict[str, Any], key: str) -> str | None:
    value = entry.get(key)
    return str(value) if value else None


def _annotate_device_with_blkid(
    device: BlockDevice, facts_by_path: dict[str, _BlkidFacts]
) -> BlockDevice:
    updated_partitions = tuple(
        _annotate_partition_with_blkid(partition, facts_by_path.get(partition.path))
        for partition in device.partitions
    )
    if updated_partitions == device.partitions:
        return device
    return device.model_copy(update={"partitions": updated_partitions})


def _annotate_partition_with_blkid(partition: Partition, facts: _BlkidFacts | None) -> Partition:
    if facts is None:
        return partition
    filesystem = (
        FilesystemInfo(fs_type=facts.fs_type, uuid=facts.uuid, label=facts.label)
        if facts.has_filesystem_data
        else None
    )
    update: dict[str, Any] = {
        "partuuid": facts.partuuid,
        "parttype": facts.parttype,
        "filesystem": filesystem,
    }
    return partition.model_copy(update=update)


# ---------------------------------------------------------------------------
# findmnt -J -> mount entries
# ---------------------------------------------------------------------------


def _parse_findmnt(text: str) -> tuple[MountEntry, ...]:
    root = _load_json(text, tool="findmnt")
    raw_entries = _require_list(root, "filesystems", tool="findmnt")
    entries: list[MountEntry] = []
    for entry in raw_entries:
        entries.extend(_parse_mount_entry(entry, parent=None))
    return tuple(entries)


def _parse_mount_entry(entry: dict[str, Any], *, parent: str | None) -> list[MountEntry]:
    target = _require_str(entry, "target", tool="findmnt")
    source = _require_str(entry, "source", tool="findmnt", context=target)
    fstype = _require_str(entry, "fstype", tool="findmnt", context=target)
    options = _require_str(entry, "options", tool="findmnt", context=target)
    results = [
        MountEntry(source=source, target=target, fstype=fstype, options=options, parent=parent)
    ]
    raw_children = entry.get("children", [])
    if not isinstance(raw_children, list):
        msg = f"findmnt: mount {target!r} has a non-list 'children' value"
        raise ValueError(msg)
    for child in raw_children:
        results.extend(_parse_mount_entry(child, parent=target))
    return results


def _annotate_device_with_mounts(
    device: BlockDevice, mounts: tuple[MountEntry, ...]
) -> BlockDevice:
    mount_by_source = {mount.source: mount for mount in mounts}
    updated_partitions = tuple(
        _annotate_partition_with_mount(partition, mount_by_source.get(partition.path))
        for partition in device.partitions
    )
    update: dict[str, Any] = {}
    if updated_partitions != device.partitions:
        update["partitions"] = updated_partitions
    own_mount = mount_by_source.get(device.path)
    if own_mount is not None:
        update["mount_point"] = own_mount.target
    if not update:
        return device
    return device.model_copy(update=update)


def _annotate_partition_with_mount(partition: Partition, mount: MountEntry | None) -> Partition:
    if mount is None:
        return partition
    update: dict[str, Any] = {"mount_point": mount.target}
    if partition.filesystem is not None:
        update["filesystem"] = partition.filesystem.model_copy(
            update={"mount_point": mount.target, "mount_options": mount.options}
        )
    return partition.model_copy(update=update)


# ---------------------------------------------------------------------------
# shared JSON-structure helpers
# ---------------------------------------------------------------------------


def _load_json(text: str, *, tool: str) -> dict[str, Any]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        msg = f"{tool}: output is not valid JSON: {exc}"
        raise ValueError(msg) from exc
    if not isinstance(data, dict):
        msg = f"{tool}: expected a JSON object at the top level, got {type(data).__name__}"
        raise ValueError(msg)
    return data


def _require_list(root: dict[str, Any], key: str, *, tool: str) -> list[dict[str, Any]]:
    value = root.get(key)
    if not isinstance(value, list):
        msg = f"{tool}: missing or non-list {key!r} key"
        raise ValueError(msg)
    for item in value:
        if not isinstance(item, dict):
            msg = f"{tool}: {key!r} contains a non-object entry"
            raise ValueError(msg)
    return value


def _require_str(entry: dict[str, Any], key: str, *, tool: str, context: str = "") -> str:
    value = entry.get(key)
    if not isinstance(value, str) or not value:
        where = f" for {context!r}" if context else ""
        msg = f"{tool}: missing or empty {key!r}{where}"
        raise ValueError(msg)
    return value


def _require_bool(entry: dict[str, Any], key: str, *, tool: str, context: str = "") -> bool:
    value = entry.get(key)
    if not isinstance(value, bool):
        where = f" for {context!r}" if context else ""
        msg = f"{tool}: missing or non-boolean {key!r}{where}"
        raise ValueError(msg)
    return value


__all__ = ["parse_storage_topology"]
