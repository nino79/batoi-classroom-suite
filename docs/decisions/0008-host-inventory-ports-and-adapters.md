# ADR-0008: Host Inventory as an Immutable, Ports-and-Adapters Core Domain

**Status:** Accepted

## Context

The Host Inventory subsystem (`bcs.inventory`) is the single source of truth describing the current machine — firmware, storage, network, identity, operating system, CPU, memory, and tooling facts. It was implemented alongside the `bcs` CLI framework, and is now being formally designed in [docs/HOST_INVENTORY.md](../HOST_INVENTORY.md), which this ADR underpins. Three properties of the existing implementation are significant enough — and costly enough to reverse later — to warrant recording here, per this project's own rule that a choice with real cost to reverse gets an ADR ([docs/decisions/README.md](README.md)):

1. Whether the subsystem's core (models, collectors, orchestration) should be allowed to know about *how* its data gets presented (CLI text/JSON/YAML today; a REST API and a Web UI tomorrow; Bash consumers in Boot Manager/Builder/Deploy eventually).
2. Whether a collected snapshot should be mutable or immutable.
3. What the canonical interchange format is for every consumer that isn't the CLI's own human-facing text output.

Boot Manager, Builder, and Deploy are all documented as intended consumers of this subsystem ([docs/architecture/boot-manager.md](../architecture/boot-manager.md), [builder.md](../architecture/builder.md), [deploy.md](../architecture/deploy.md)), and none of them exist yet — so this decision is made ahead of those components, and must hold up without knowing their exact final shape.

## Decision

1. **Ports-and-adapters (hexagonal) split.** `bcs.inventory.models`, `bcs.inventory.collectors`, and `bcs.inventory.service` form the core domain: they perform no printing, no argument parsing, and no HTTP, and depend on no presentation or transport framework (no Typer, no Rich, no web framework). `bcs.commands.inventory` and `bcs.commands.doctor` are adapters over that core today; a future REST API adapter and a future Web UI (itself a client of that REST API, not a third direct adapter) are expected to be added the same way, without modifying the core. See the dependency graph in [docs/HOST_INVENTORY.md § Dependency Graph](../HOST_INVENTORY.md#dependency-graph).
2. **Immutability.** Every model in `bcs.inventory.models` is a frozen Pydantic model (`FrozenModel`/`FrozenExtensibleModel`, `model_config = ConfigDict(frozen=True, ...)`). A `HostInventory` instance is a point-in-time snapshot; a change on the machine produces a new snapshot object, never a mutation of an old one.
3. **JSON as the canonical interchange format.** `model_dump(mode="json", by_alias=True)` — `camelCase` keys, ISO-8601 UTC timestamps, enums as string values — is the one wire format every non-human consumer (a future REST response body, a future Boot Manager/Builder/Deploy Bash script via `jq`) is expected to read. YAML and Rich text remain CLI-only human-convenience renderings of the same data, never a second format with independent guarantees. `HostInventory` carries its own `schemaVersion` (`bcs-inventory/v1alpha1`), versioned independently of `bcs-cli/v1alpha1` (the CLI's own output envelope) and `bcs/v1alpha1` (ClassroomConfig).

### Alternatives Considered

- **Let the CLI command module own collection logic directly** (no separate `inventory` package). Rejected: this is exactly the duplicated-hardware-detection risk the subsystem exists to eliminate — `bcs doctor` already needed the same facts `bcs inventory` collects, and a future REST API would have needed a third copy.
- **Mutable, cache-and-refresh model** (a `HostInventory` object with a `.refresh()` method). Rejected: a mutable shared inventory object introduces exactly the aliasing/staleness hazards immutability is meant to avoid — a consumer holding a reference could observe it change underneath it. A cheap-to-construct immutable snapshot, re-collected whenever fresh data is needed, is simpler to reason about and cheap enough in practice (collection is a handful of file reads, not an expensive scan).
- **XML** as the interchange format, for parity with some enterprise config-management tooling. Rejected: no consumer in this project's ecosystem (Bash via `jq`, a future Python REST framework, a future JS-based Web UI) benefits from XML over JSON; it would add a serialization library dependency for no corresponding gain.
- **Protobuf/gRPC** for the future REST/agent transport. Rejected as premature: it would require a schema-compilation step and a new dependency before there is a concrete second consumer to justify the added operational complexity; JSON over HTTP is sufficient for the fleet sizes described in [NFR-002](../../SPECIFICATION.md#3-non-functional-requirements) and keeps the transport debuggable with tools every technician already has (`curl`, `jq`).
- **A dynamic `Collector` protocol/registry**, allowing third parties to register new collectors without editing `bcs.inventory.collectors` directly. Considered and explicitly not adopted now — see [docs/HOST_INVENTORY.md § Proposed Changes Requiring Approval, item 4](../HOST_INVENTORY.md#proposed-changes-requiring-approval): there is no concrete second contributor yet, and building the abstraction ahead of a real need is the proportionality risk [REVIEW.md §7](../../REVIEW.md#7-a-meta-concern-proportionality) already flags for this project.

## Consequences

- `HostInventory` and its sections can be handed directly to a Pydantic-native web framework as a response model with no adaptation code, the concrete benefit realized in [docs/HOST_INVENTORY.md § Interaction with a Future REST API](../HOST_INVENTORY.md#interaction-with-a-future-rest-api).
- Every new fact area added to the core (e.g., a future `caveats` field, per [docs/HOST_INVENTORY.md § Proposed Changes, item 1](../HOST_INVENTORY.md#proposed-changes-requiring-approval)) is automatically available to every adapter — CLI, REST, Web UI, Bash — without adapter-specific work.
- Collectors and the core domain must continue to be held to a stricter discipline than ordinary application code: no `print()`, no framework imports, defensive-but-never-crashing behavior on missing facts. This is an ongoing review burden, not a one-time cost — a future contributor adding a ninth collector must be held to the same rule.
- Because snapshots are immutable, any code that wants to observe change over time (e.g., a future "has this machine's hardware changed since last inventory" check) must explicitly collect and compare two snapshots; the subsystem itself does not track history or diffs.
- This ADR does not resolve the REST API's topology (local per-machine agent vs. central aggregator) — that is recorded as an open question in [docs/HOST_INVENTORY.md § Open Questions](../HOST_INVENTORY.md#open-questions--explicitly-deferred), deliberately deferred until a real Deploy implementation drives the requirement.
- Accepted per the user's explicit approval of [docs/HOST_INVENTORY.md](../HOST_INVENTORY.md); this does not, by itself, approve the individual items in that document's [Proposed Changes Requiring Approval](../HOST_INVENTORY.md#proposed-changes-requiring-approval) list (the `caveats` field, the checked-in JSON Schema artifact, the golden-file regression test, and the deferred Collector-Protocol option) — each remains its own open, separately approvable item.

## Amendment: EFI System Partition and USB Storage

This ADR is recorded here as an amendment rather than superseded by a new ADR, per the maintainers' explicit direction, since it extends rather than reverses the Decision above: the schema is growing additively within the same ports-and-adapters/immutability/JSON-canonical design this ADR already established, not changing that design. Status remains **Accepted**.

### Context

Implementing the detectors listed in this subsystem's requirements surfaced two facts not covered by the original schema: the EFI System Partition (ESP) — already a hard requirement for Builder (`BLD-004`) and Deploy (`DEP-003`), but never modeled as a Host Inventory fact a running machine can be asked about — and USB-attached storage, relevant because a technician's recovery/deployment media is typically a USB drive. Both require a modeling decision the original schema didn't make, and a genuine scoping decision (how much of "USB" to model) with a real cost either way — implementing too little forces a later breaking redesign, too much invents unused surface area — so it is recorded here rather than guessed at implementation time.

### Decision

1. **The EFI System Partition becomes a first-class model, `EfiSystemPartition`, and a first-class field, `HostInventory.efiSystemPartition`.** It is not folded into `FirmwareInfo` (which stays a firmware-only fact area: UEFI presence, Secure Boot state, firmware vendor/version) nor into `StorageDevice` (which models whole block devices, e.g. `/dev/nvme0n1`, not partitions). The ESP has its own lifecycle facts — filesystem, mount state, free space — that fit neither cleanly, and giving it its own model keeps both existing models' scope unchanged.
2. **Host Inventory models USB *storage* devices only, as `UsbStorageDevice`, not USB devices in general.** `HostInventory.usbStorage` is a list of storage devices suitable for booting or deployment (e.g. a recovery USB drive). Keyboards, mice, webcams, hubs, and other USB peripherals are explicitly out of scope and will not be added under this model.
3. Both are additive fields on `HostInventory`; per this document's existing versioning policy ([docs/HOST_INVENTORY.md § Serialization Strategy](../HOST_INVENTORY.md#serialization-strategy)), `schemaVersion` (`bcs-inventory/v1alpha1`) does not change.

### Alternatives Considered

- **Add `esp_present`/`esp_path` fields directly to `FirmwareInfo`.** Rejected: it would conflate a firmware-only fact area with a partition-level, filesystem-bearing fact area (mount state, free space) that has nothing to do with firmware itself, and would need to grow `FirmwareInfo` awkwardly every time an ESP-specific fact is added later.
- **Extend `StorageDevice` with partition-level detail (a `partitions: list[PartitionInfo]` field), then flag which partition is the ESP.** Rejected as disproportionate: it would turn `StorageDevice` from "one whole block device" into a full partition table model to serve a single, specific, already-well-understood partition, when BCS only ever needs to ask "where is *the* ESP and is it mounted," not "enumerate all partitions of all disks."
- **Model USB devices generically (vendor ID, product ID, device class — `lsusb`-style), covering all USB peripherals.** Rejected: nothing in this subsystem's stated purpose ([docs/HOST_INVENTORY.md § Purpose](../HOST_INVENTORY.md#purpose)) or in any of Boot Manager/Builder/Deploy's documented needs consumes information about a USB keyboard or hub. Modeling it anyway is exactly the kind of speculative flexibility [REVIEW.md §7](../../REVIEW.md#7-a-meta-concern-proportionality) already argues against for this project; USB *storage* is the only USB fact any documented consumer has a concrete use for (identifying viable boot/recovery media).

### Consequences

- `EfiSystemPartition` and `UsbStorageDevice` follow the same immutability and `x-`-extension rules as every other model in this subsystem (`FrozenModel`, per [docs/HOST_INVENTORY.md § Pydantic Models](../HOST_INVENTORY.md#pydantic-models)).
- `bcs doctor` is expected to gain two new checks (`esp`, `usb-storage`) evaluating these same facts, following the existing pattern where doctor checks evaluate pass/fail against Host Inventory collectors rather than re-probing the host — see [docs/CLI.md](../CLI.md#bcs-doctor).
- None of this is implemented yet: no `collect_efi_system_partition()`, no `collect_usb_storage()`, no `bcs doctor` checks for either. This amendment records the schema decision only; implementation remains gated on separate approval, per [docs/HOST_INVENTORY.md § Current Implementation Status](../HOST_INVENTORY.md#current-implementation-status-vs-this-proposal).
