# Storage Adapter — Design Proposal (Block Storage, Partitions, Filesystems)

> **Status: Accepted; fully implemented.** This document is the authoritative design for the Storage Adapter, the second Host Discovery adapter in BCS's Platform Layer. It follows the same ports-and-adapters architecture as the [EFI Adapter](EFI_ADAPTER.md). **Implemented:** `BlockDevice`/`Partition`/`FilesystemInfo`/`MountEntry`/`StorageConfiguration` (`cli/src/bcs/platform/adapters/storage/models.py`, per [§ Pydantic Models](#pydantic-models)); `StorageError`/`StorageUnavailableError`/`StorageParseError` (`cli/src/bcs/platform/adapters/storage/errors.py`, per [§ Error Hierarchy](#error-hierarchy)); `parse_storage_topology` (`cli/src/bcs/platform/adapters/storage/parser.py`, per [§ Parser Architecture](#parser-architecture)); `read_storage_topology` (`cli/src/bcs/platform/adapters/storage/adapter.py`, per [§ Adapter Responsibilities](#adapter-responsibilities)) — the complete adapter as designed in this document.

## Purpose

This is the second of BCS's **Host Discovery** adapters — read-only Platform Layer adapters that turn Linux system-inspection tool output into typed, immutable BCS models, per [docs/PLATFORM_LAYER.md § How Future Adapters Use It](PLATFORM_LAYER.md#how-future-adapters-use-it). This one wraps standard Linux block-device tools (`lsblk`, `blkid`, `findmnt`) to provide comprehensive storage topology: all block devices, all partitions with their type GUIDs, all filesystem metadata, and all mount entries.

Two needs motivate it:

1. **Host Inventory's storage gap.** `CLI-015` and `CLI-016` require the Host Inventory snapshot to report EFI System Partition details (presence, device/partition, filesystem, mount state, size) and enumerate USB storage devices. The existing `collect_storage()` in `bcs.inventory.collectors` uses `sysfs` directly — this adapter provides a more robust, tool-based approach with richer data (filesystem types, UUIDs, labels, mount options) that complements and eventually replaces the `sysfs` collector.
2. **Builder and Deploy requirements.** `BLD-004` (GPT + ESP layout), `DEP-003` (disk layout restoration), and `PLAT-005` (NVMe primary target) all require BCS to have accurate, structured knowledge of the current storage topology before deployment operations begin. The Storage Adapter provides this knowledge as raw facts. Which device is "primary", "system", "boot", or "installation target" is a decision made by domain services that consume this adapter's output — not by the adapter itself.

## Scope

This adapter is **read-only**. It never creates, modifies, or deletes partitions, filesystems, or mount points. Any storage *management* capability (partitioning, formatting, mounting) is a separate adapter, a separate design document, and a separate ADR — never a silent extension of this one.

## Linux Storage Tools

The adapter wraps three standard Linux tools, each chosen for specific data they provide:

| Tool | Purpose | Key Data |
|------|---------|----------|
| `lsblk -J -b` | Block device tree | Devices, partitions, size, type, mount point |
| `blkid -p -o json` | Filesystem metadata | UUID, type, label, PARTUUID |
| `findmnt -J` | Mount topology | Mount points, sources, fstype, options |

All three are present on every standard Linux system (util-linux package) and produce JSON output with `LANG=C LC_ALL=C` forced, ensuring stable, parseable output regardless of locale.

## Package Structure

```
cli/src/bcs/platform/adapters/
└── storage/                       # the storage domain.
    │                              # NOT named "lsblk": the package survives
    │                              # a future backend swap (libblkid, sysfs direct, ...)
    ├── __init__.py                # [implemented] re-exports StorageConfiguration, BlockDevice,
    │                              # Partition, FilesystemInfo, MountEntry, parse_storage_topology,
    │                              # read_storage_topology, StorageError, StorageUnavailableError,
    │                              # StorageParseError
    ├── models.py                  # [implemented] BlockDevice, Partition, FilesystemInfo,
    │                              # MountEntry, StorageConfiguration
    │                              # (frozen, JSON-serializable) - see § Pydantic Models
    ├── parser.py                  # [implemented] parse_storage_topology(lsblk_output: str,
    │                              # blkid_output: str, findmnt_output: str) -> StorageConfiguration
    │                              # (pure function, no subprocess, no CommandRunner, no
    │                              # PlatformError hierarchy - raises plain ValueError, mirroring
    │                              # the EFI parser exactly - see § Parser Architecture)
    ├── adapter.py                 # [implemented] read_storage_topology(runner: CommandRunner) ->
    │                              # StorageConfiguration - the only place this package calls
    │                              # CommandRunner.run(), and the only place that knows the
    │                              # current backend is lsblk/blkid/findmnt
    └── errors.py                  # [implemented] StorageError(PlatformError),
                                    # StorageUnavailableError, StorageParseError
```

## Pydantic Models

**Implemented** (`cli/src/bcs/platform/adapters/storage/models.py`; see `cli/tests/test_platform_adapters_storage_models.py` for the corresponding test coverage). All models are frozen, JSON-serializable, and use camelCase aliases for all field names. They live in `models.py` and are exported from `__init__.py`. Every field represents an observed fact only — no field interprets, selects, or ranks a device/partition (e.g. `parttype` is reported as a raw GUID string, never resolved to "this is the ESP"); the only validation performed is internal data consistency (`size_bytes >= 0`, `Partition.number >= 1`, no duplicate `Partition.number` within one `BlockDevice`, no duplicate `BlockDevice.path` within one `StorageConfiguration`) — the same category of "narrow, direct implementation of a constraint already implied by this document's own field description" already established for the EFI Adapter's models, not a new design decision.

### BlockDevice

Represents a whole block device (e.g., `/dev/nvme0n1`, `/dev/sda`).

```
BlockDevice
├── name: str              # Device name without /dev/ prefix (e.g., "nvme0n1")
├── path: str               # Full device path (e.g., "/dev/nvme0n1")
├── device_type: str        # "disk" | "part" | "rom" | "loop" | "raid" | ...
├── size_bytes: int | None  # Size in bytes, or None if unknown
├── is_removable: bool     # True for USB/removable media
├── is_read_only: bool      # True if read-only device
├── is_nvme: bool           # True if NVMe device (name starts with "nvme")
├── model: str | None       # Device model string, or None
├── vendor: str | None      # Device vendor string, or None
├── serial: str | None      # Device serial number, or None
├── partitions: list[Partition]  # Child partitions (empty for non-disk devices)
└── mount_point: str | None # Mount point if the whole device is mounted, else None
```

### Partition

Represents a partition within a block device (e.g., `/dev/nvme0n1p1`).

```
Partition
├── name: str               # Partition name (e.g., "nvme0n1p1")
├── path: str               # Full partition path (e.g., "/dev/nvme0n1p1")
├── number: int             # Partition number (1-based)
├── size_bytes: int | None  # Size in bytes, or None if unknown
├── partuuid: str | None    # Partition UUID (GPT)
├── parttype: str | None    # Partition type GUID (GPT, e.g. "C12A7328-F81F-11D2-BA4B-00A0C93EC93B" for ESP)
├── filesystem: FilesystemInfo | None  # Filesystem on this partition
└── mount_point: str | None # Mount point if mounted, else None
```

### FilesystemInfo

Represents filesystem metadata on a partition or whole device.

```
FilesystemInfo
├── fs_type: str | None     # Filesystem type (e.g., "vfat", "ext4", "xfs", "swap")
├── uuid: str | None        # Filesystem UUID
├── label: str | None       # Filesystem label
├── mount_options: str | None  # Mount options (e.g., "rw,relatime")
└── mount_point: str | None  # Current mount point, or None
```

### MountEntry

Represents a mount point from `findmnt`, providing detailed mount topology.

```
MountEntry
├── source: str              # Mount source (device path, UUID=<uuid>, LABEL=<label>, ...)
├── target: str             # Mount point (e.g., "/boot/efi")
├── fstype: str             # Filesystem type (e.g., "vfat", "ext4")
├── options: str            # Mount options (comma-separated)
└── parent: str | None      # Parent mount point (for bind mounts), or None
```

### StorageConfiguration

The top-level model returned by the adapter — the complete storage topology snapshot.

```
StorageConfiguration
├── devices: list[BlockDevice]  # All block devices (disks and their partitions)
└── mounts: list[MountEntry]    # All mount points
```

## Parser Architecture

**Implemented** (`cli/src/bcs/platform/adapters/storage/parser.py`; see `cli/tests/test_platform_adapters_storage_parser.py` for the corresponding test coverage). The parser (`parser.py`) is a **pure function** with no knowledge of subprocess, CommandRunner, or where its input came from:

```python
def parse_storage_topology(
    lsblk_output: str,
    blkid_output: str,
    findmnt_output: str,
) -> StorageConfiguration:
    ...
```

### Design Decision: Three-Tool Composition

The parser accepts three separate text inputs (one per tool) rather than a single combined output. Rationale:

1. **Each tool has distinct output semantics.** `lsblk -J` gives device tree structure; `blkid -p -o json` gives per-partition filesystem metadata; `findmnt -J` gives mount topology. Combining them into one parser call would require either (a) a complex multi-tool orchestrator inside the parser (violating single-responsibility) or (b) a single tool that doesn't exist.
2. **The adapter (not the parser) orchestrates.** The adapter calls each tool, collects each output, and passes all three to the parser. This keeps the parser pure and testable with isolated inputs.
3. **Error isolation.** If one tool fails, the adapter can decide what to do (partial data, error propagation) without the parser needing to know about tool failures.

### Parser Steps

1. **Parse `lsblk` JSON** → build device tree (BlockDevice + Partition nodes)
2. **Parse `blkid` JSON** → annotate partitions with FilesystemInfo (uuid, type, label, partuuid)
3. **Parse `findmnt` JSON** → build MountEntry list
4. **Cross-reference** → merge mount data into device tree (set `mount_point` on Partition nodes)
5. **Return StorageConfiguration**

### Error Handling in Parser

**Amended during implementation, to match the EFI parser's own precedent exactly** (`bcs.platform.adapters.efi.parser`, per [ADR-0010](decisions/0010-efi-adapter-read-only-scope.md)): the parser raises plain `ValueError` on malformed JSON, a missing top-level array, or an entry missing a field the parser cannot proceed without — naming the tool and the specific problem — and lets `pydantic.ValidationError` propagate for model-level invariants (duplicate device paths, duplicate partition numbers). It does **not** import or raise `StorageParseError` — that would pull the Platform Layer's `PlatformError` hierarchy into a module whose independence from execution/error-translation concerns is a load-bearing property, the same reasoning that keeps `bcs.platform.adapters.efi.parser` free of `FirmwareBootParseError`. Translating a caught `ValueError` into `StorageParseError` is `adapter.py`'s job, once it exists — see `bcs.platform.adapters.efi.adapter` for the exact pattern this adapter is expected to follow. The parser does not catch tool-level errors either way — those remain the adapter's responsibility (tool not found, non-zero exit code, timeout).

## Adapter Responsibilities

**Implemented** (`cli/src/bcs/platform/adapters/storage/adapter.py`; see `cli/tests/test_platform_adapters_storage_adapter.py` for the corresponding test coverage). The adapter (`adapter.py`) is the only module that knows about `CommandRunner`:

```python
def read_storage_topology(
    runner: CommandRunner,
    *,
    timeout_seconds: float | None = 10.0,
) -> StorageConfiguration:
    ...
```

### Command Execution

The adapter executes three commands in sequence, stopping (and raising) at the first failure rather than running the remaining tools:

| # | Command | Timeout | Rationale |
|---|---------|---------|-----------|
| 1 | `lsblk -J -b` | 10s | Block device tree; `-b` forces byte output |
| 2 | `blkid -p -o json` | 10s | Filesystem metadata for all block devices |
| 3 | `findmnt -J` | 10s | Mount topology |

All three commands are **read-only** and have no side effects. Locale is forced to `LANG=C LC_ALL=C` via the CommandRunner's environment (standard Platform Layer behavior), built once and reused for all three calls. `timeout_seconds` is one parameter applied identically to all three invocations, per the uniform 10s budget above (a single value, not three independently-tunable ones) — mirroring the EFI adapter's own single-parameter simplicity.

### Error Mapping

**Amended during implementation, to match the EFI adapter's own precedent exactly** (`bcs.platform.adapters.efi.adapter`): `CommandNotFoundError`/`CommandTimeoutError` — raised by `CommandRunner.run()` itself when a tool is missing from `PATH` or exceeds its timeout — propagate **unchanged**, the same choice the EFI adapter already made for `efibootmgr`. This reading is also the one consistent with `StorageUnavailableError`'s own docstring (`errors.py`): "one or more of the required tools *is present and executable*, but the environment cannot provide usable storage data" — a tool missing from `PATH` entirely is a different, already-typed condition, not this adapter's to re-wrap. `StorageUnavailableError` is instead used the way `FirmwareBootUnavailableError` is: for a non-zero exit whose `stderr` recognisably indicates an environment problem (permission denied, a vanished device node, etc.), checked via a pattern set analogous to the EFI adapter's own `_is_unavailable`.

| Condition | Adapter action |
|---|---|
| `lsblk`/`blkid`/`findmnt` not on `PATH` | `CommandNotFoundError` — raised automatically by `CommandRunner`; the adapter does no translation. |
| A tool's `runner.run()` call exceeds its timeout | `CommandTimeoutError` — raised automatically by `CommandRunner`, propagated unchanged. |
| A tool exits non-zero, `stderr` recognisably indicates the environment cannot provide storage data | `StorageUnavailableError`, carrying the full result. |
| A tool exits non-zero, not recognisable as the above | `StorageError` (the base class itself), carrying the full result. |
| All three tools succeed but `parse_storage_topology` raises `ValueError` | `StorageParseError`, chained (`raise ... from exc`) from the original `ValueError`. |

### Partition Type GUID

The adapter reports each partition's type GUID as a raw fact via the `parttype` field on `Partition`. The standard GPT EFI System Partition type GUID is `C12A7328-F81F-11D2-BA4B-00A0C93EC93B`. Domain services that need to identify ESP-like partitions filter by this GUID. The adapter does not interpret the GUID — it reports it as observed.

## Error Hierarchy

```
PlatformError (from bcs.platform.errors)
└── StorageError (base for all storage adapter errors)
    ├── StorageUnavailableError  # Tool not found, permission denied, device missing
    └── StorageParseError         # Malformed output, unexpected structure
```

All three extend `PlatformError` and are exported from `__init__.py`.

## Locale Policy

This adapter follows the Platform Layer-wide locale policy: every subprocess call forces `LANG=C` and `LC_ALL=C` via `os.environ.copy()` + overrides passed to `subprocess.run()`. This is handled by `SubprocessCommandRunner` and does not need to be implemented in the adapter itself — it is a property of the execution layer, not the adapter.

## Command Metadata

Command metadata (which tool was called, exit code, duration) does **not** belong on `StorageConfiguration`. The same reasoning from [EFI_ADAPTER.md § Command Metadata](EFI_ADAPTER.md#command-metadata) applies: the model represents domain facts (storage topology), not execution provenance. If execution provenance is needed for debugging, it is available from `CommandResult` returned by `CommandRunner.run()`.

## Relationship to Existing Inventory Collectors

The existing `collect_storage()` in `bcs.inventory.collectors` uses `sysfs` directly to enumerate block devices. The Storage Adapter provides richer data (filesystem types, UUIDs, labels, mount options) and uses standard tools that are more portable and better maintained.

**Migration path:** The Storage Adapter is implemented first. Then `bcs.inventory.collectors.collect_storage()` is refactored to call `read_storage_topology()` internally, replacing the `sysfs` implementation. The `StorageConfiguration` model becomes the canonical storage data source for Host Inventory.

**Existing models in `bcs.inventory.models`:**
- `StorageDevice` — existing inventory model (name, path, is_nvme, size_bytes, model)
- `UsbStorageDevice` — existing inventory model (extends StorageDevice with vendor, mounted, mount_point)
- `EfiSystemPartition` — existing inventory model (device, partition_number, filesystem, mount_state, size_bytes)

The Storage Adapter's models are **Platform Layer** models (in `bcs.platform.adapters.storage.models`), not inventory models. The translation from `StorageConfiguration` → `HostInventory` (which uses `StorageDevice`, `UsbStorageDevice`, `EfiSystemPartition`) is the responsibility of the inventory collector, not the adapter.

## Testing Strategy

### Unit Tests (models) — implemented

`BlockDevice`/`Partition`/`FilesystemInfo`/`MountEntry`/`StorageConfiguration` are covered directly, no fixtures or mocking needed — construction and defaults, both alias spellings (`populate_by_name`), every validator (`size_bytes`/`number` bounds, the two duplicate-identifier checks), immutability, equality, hashability, and JSON round-tripping (including nested models) for each model. See `cli/tests/test_platform_adapters_storage_models.py`; `models.py` is at 100% statement and branch coverage.

### Unit Tests (parser) — implemented

`parse_storage_topology` is covered by `cli/tests/test_platform_adapters_storage_parser.py`: every well-formed scenario named below, each malformed-input case per tool (invalid JSON, a missing top-level array, an entry missing a required field), the two model-level `ValidationError` cases (duplicate device paths, duplicate partition numbers), and — via AST inspection, not a substring search — that the module imports nothing beyond `json`/`typing`/its own models. The real corpus (`cli/tests/fixtures/storage/`) holds only zero-byte placeholders for the three representative scenarios below (see that directory's README), so these tests build a *temporary*, `tmp_path`-rooted corpus mirroring the real one's layout and load every scenario through `fixture_utils.load_fixture`/`fixture_path` — never an inline string passed straight to the parser — exactly the approach `cli/tests/test_platform_adapters_efi_parser.py` used before real `efibootmgr` captures existed. Once real captures replace the placeholders, this test module is expected to switch to loading them directly.

Representative hardware scenarios (the three with real-corpus placeholders reserved):

- **Typical NVMe laptop**: single NVMe disk, GPT+ESP, one Linux partition
- **Classroom machine**: NVMe disk, multiple partitions (ESP, root, home, swap)
- **USB recovery drive**: removable USB disk, single partition, vfat

Each is a triple of outputs (one per tool) corresponding to the same system state, so cross-referencing tests can verify correct merging. **Malformed output** (truncated JSON, missing fields, unexpected structure) is deliberately tested only via the synthetic corpus, not as real-corpus placeholders — malformed output is not something a healthy real system produces to capture, mirroring how the EFI Adapter's own malformed-line scenarios were never added to `cli/tests/fixtures/firmware/`'s inventory either.

### Unit Tests (adapter) — implemented

`read_storage_topology` is covered by `cli/tests/test_platform_adapters_storage_adapter.py`, following exactly the same `FakeCommandRunner`-based philosophy as `test_platform_adapters_efi_adapter.py` (a configurable stand-in for `CommandRunner`, keyed by tool name here since three tools are involved, never a mock of `SubprocessCommandRunner`, zero real subprocess execution): correct commands/arguments/order, `check=False` and locale-forced `env` (with `PATH` preserved) on every call, timeout forwarded identically to all three calls (including the `10.0` default and an explicit `None`), a correctly-parsed `StorageConfiguration` on success, `CommandNotFoundError`/`CommandTimeoutError` propagating unchanged from whichever of the three tools raises them, that no further tool runs once one has failed, `StorageUnavailableError` for each recognised "environment unavailable" `stderr` pattern from each of the three tools, `StorageError` for an unrecognised non-zero exit, and `StorageParseError` — with `__cause__` preserved — when parsing fails.

### Integration Tests (real environment) — not implemented

The adapter is not yet tested against a controlled Linux environment (CI with loop devices or a VM snapshot) — mirroring the EFI adapter's own "real end-to-end, optional, environment-gated" test, which is also not implemented. Recorded here as a future addition, not required for this implementation.

### Contract Tests

A fixture-based test verifies that `parse_storage_topology` output is stable across tool version changes (within the same major version of util-linux). This guards against silent output format changes.

## Backward Compatibility

This design is additive only:

- No changes to `bcs.platform.models.CommandResult`, `bcs.platform.errors.PlatformError`, `bcs.platform.execution.CommandRunner`, or `bcs.platform.execution.SubprocessCommandRunner`
- No changes to existing inventory models (`StorageDevice`, `UsbStorageDevice`, `EfiSystemPartition`)
- No changes to `bcs.inventory.collectors` (migration is a follow-up task)
- No changes to the Host Inventory JSON schema (CLI-012) — the Storage Adapter's models are Platform Layer internal, not Host Inventory output

## Future Extensibility

### LVM Support

LVM logical volumes (`/dev/mapper/*`, `/dev/vg/lv`) are reported by `lsblk` as device type `lvm`. The current design does not explicitly handle LVM topology (volume groups, logical volumes, physical volumes). If LVM support is needed, a future amendment adds `LvmVolumeGroup`, `LvmLogicalVolume`, and `LvmPhysicalVolume` models, and the parser is extended to parse `pvs -o json` and `vgs -o json` output.

### RAID Support

`lsblk` reports `md` (Linux software RAID) devices. The current design includes them as `BlockDevice` with `device_type="raid"` but does not parse `/proc/mdstat` for RAID details (active drives, degraded state, sync status). If RAID support is needed, a future amendment adds `RaidArray` and `RaidMember` models.

### NVMe SMART Data

`nvme smartlog -o json /dev/nvme0n1` provides SMART data for NVMe devices. This is out of scope for v1.0 but could be added as an optional `NvmeSmartInfo` model on `BlockDevice` if `nvme` tool is available.

## Open Questions

1. **Should the adapter also call `df -B1 --output=...` for usage statistics?** The existing `collectors.py` uses `os.statvfs()` for usage data. Adding `df` output to the adapter would provide filesystem usage statistics (total, used, free bytes) that could populate `FilesystemInfo`. However, this data changes frequently and may not be appropriate for a "snapshot" model. **Recommendation:** Defer; usage data can be queried live when needed.

2. **Should `blkid` be called per-partition or once for all?** `blkid -p -o json` returns metadata for all block devices. However, on systems with many devices, this can be slow. An alternative is to call `blkid` only for partitions identified by `lsblk`. **Recommendation:** Start with `blkid -p -o json` (all devices); optimize to per-partition calls only if profiling shows a problem.

3. **Should the adapter detect LUKS encrypted containers?** `lsblk` reports `crypt` type devices. The current design does not handle LUKS metadata. If encrypted root/disk support is needed, this is a separate design. **Recommendation:** Out of scope for v1.0.

4. **Should the adapter report device WWN (World Wide Name)?** `lsblk -J -b` does not include WWN by default. `lsblk -J -b -o NAME,SIZE,TYPE,ROTA,MODEL,Serial,WWN` would add it, but requires specifying columns explicitly. **Recommendation:** Defer; serial number is sufficient for v1.0.

## ADR Recommendation

This design does **not** require a new ADR. It is fully consistent with existing ADRs:

- **ADR-0008** (Ports and Adapters for Host Discovery): This is the second adapter following the pattern established by ADR-0008's first implementation (EFI Adapter).
- **ADR-0009** (Platform Layer Command Runner): The adapter uses `CommandRunner` as designed in ADR-0009.
- **ADR-0010** (EFI Adapter): This design follows the exact same architecture as ADR-0010's implementation.

The Storage Adapter is the natural continuation of the architecture already accepted in ADR-0008 and ADR-0010. If the reviewer disagrees and believes a new ADR is needed, the recommendation is **ADR-0011: Storage Adapter (Block Storage, Partitions, Filesystems)**.

## Summary of Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Package name | `bcs.platform.adapters.storage` | Domain-driven naming; survives backend swap |
| Top-level model | `StorageConfiguration` | Complete storage topology snapshot |
| Parser inputs | Three separate text inputs (lsblk, blkid, findmnt) | Each tool has distinct output semantics; error isolation |
| ESP reporting | Partition type GUID as raw fact (`parttype` field) | Adapter reports facts; domain services interpret |
| NVMe reporting | All NVMe devices in `block_devices` list | Adapter reports facts; domain services apply selection policy |
| Error hierarchy | `StorageError` → `StorageUnavailableError`, `StorageParseError` | Consistent with `FirmwareBootError` pattern |
| Command metadata | Not on model | Domain facts vs. execution provenance separation |
| LVM/RAID support | Not in v1.0 | Out of scope; design allows future extension |
| New ADR needed | No (or ADR-0011 if reviewer requires) | Consistent with existing ADRs |