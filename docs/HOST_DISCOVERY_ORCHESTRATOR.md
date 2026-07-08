# Host Discovery Orchestrator — Design Proposal (Coordinating Discovery Adapters into Host Inventory)

> **Status: Accepted; data-holding types, coordination logic, Host Inventory integration, and composition-root/`RuntimeContext` wiring implemented (Parts 1–4).** This document designs the Host Discovery Orchestrator: the component that coordinates every Host Discovery adapter (Platform Layer adapters and legacy `sysfs`-based collectors alike) and aggregates their output into a form consumable by [Host Inventory](HOST_INVENTORY.md). See [ADR-0011](decisions/0011-host-discovery-orchestrator.md) (status: `Accepted`) for the architectural decision this document expands. **Implemented:** `HostDiscoveryAdapters`/`HostDiscoverySnapshot` (`cli/src/bcs/inventory/discovery/models.py`), `HostDiscoveryOrchestrator` (`cli/src/bcs/inventory/discovery/orchestrator.py`, per [§ Public API](#public-api) and [§ Error Propagation](#error-propagation)), `bcs.inventory.service.collect_host_inventory()`'s optional `orchestrator` parameter (`cli/src/bcs/inventory/service.py`, per [§ Relationship to Host Inventory](#relationship-to-host-inventory---implemented)), and `bcs.app.main()`'s composition-root wiring plus `RuntimeContext.host_discovery_orchestrator` (`cli/src/bcs/app.py`, `cli/src/bcs/context.py`, per [§ Dependency Injection Strategy](#dependency-injection-strategy---implemented) and [§ Lifecycle](#lifecycle---implemented)). **Not yet implemented:** `bcs.commands.inventory`/`bcs inventory` actually passing `runtime.host_discovery_orchestrator` into `collect_host_inventory()` - the orchestrator is built and available on every `RuntimeContext`, but no command consumes it yet.

## Purpose

Two already-documented, previously-deferred questions motivate this component:

1. [docs/PLATFORM_LAYER.md § Open Questions](PLATFORM_LAYER.md#open-questions--explicitly-deferred) explicitly defers "migrating `bcs.inventory.collectors` to accept an injected `CommandRunner`" as "its own follow-on design/approval step once a first real adapter... is actually being built." Two adapters (EFI, Storage) now exist or are designed; this document is that follow-on step.
2. [docs/EFI_ADAPTER.md § Open Questions](EFI_ADAPTER.md#open-questions) and [docs/STORAGE_ADAPTER.md § Relationship to Existing Inventory Collectors](STORAGE_ADAPTER.md#relationship-to-existing-inventory-collectors) each independently ask the same unanswered question — "what exposes this adapter's output to a `bcs` command / `HostInventory`?" — without referencing each other. This document answers it once, for every current and future Discovery adapter, rather than leaving each adapter to keep re-asking it.

The Host Discovery Orchestrator is the single place that knows *which* Discovery adapters exist for a given `bcs` build and calls each of them. Nothing above it (`bcs.inventory.service`, `bcs.commands.inventory`, `bcs.commands.doctor`) needs to enumerate adapters itself, and nothing below it (an individual adapter) needs to know it is one of several being coordinated.

## Aggregation-Only Guarantee

Mirroring [docs/EFI_ADAPTER.md § Read-Only Guarantee](EFI_ADAPTER.md#read-only-guarantee), this is a hard, non-negotiable constraint on this component's scope, not a style preference:

- **This component never executes a Linux command.** It imports no adapter's `adapter.py` (the module that calls `CommandRunner.run()`); it only ever receives already-bound, zero-argument callables (see [§ Public API](#public-api)) that some other, upstream code has already connected to a `CommandRunner`.
- **This component never imports `subprocess`.**
- **This component never imports `bcs.platform.execution.CommandRunner`.** Its only structural dependency on the Platform Layer is on adapters' *model* modules (`bcs.platform.adapters.efi.models`, `bcs.platform.adapters.storage.models`, ...) for type annotations — data shapes, not execution.
- **This component never decides an installation target, a preferred disk, a preferred ESP, a boot order, or an operating system.** It has no concept of "preferred" or "selected" anything. Every field it produces is either exactly what an adapter returned, or absent (`None`) — it never filters, ranks, merges, or interprets adapter output. Contrast [docs/STORAGE_ADAPTER.md § Purpose](STORAGE_ADAPTER.md#purpose): "Which device is 'primary'... is a decision made by domain services that consume this adapter's output" — this component is not that domain service, and never becomes one.
- If a future need for such a decision arises (e.g. "which partition is the ESP for this deployment"), it is a **separate component, with its own separate design document**, consuming this orchestrator's output — never a silent extension of it.

## Package Structure

```
cli/src/bcs/inventory/
├── __init__.py
├── models.py                   # HostInventory (existing) - unaffected by this design
├── collectors.py                # existing sysfs-based collect_* functions - unaffected;
│                                # several (collect_cpu, collect_memory, collect_network) are
│                                # reused as-is, see § Dependency Injection Strategy
├── service.py                    # [implemented] existing collect_host_inventory() - gains an
│                                # optional orchestrator dependency; see § Relationship to Host
│                                # Inventory
└── discovery/                    # NEW - this design
    ├── __init__.py                 # [implemented] re-exports HostDiscoveryAdapters,
    │                              # HostDiscoverySnapshot, HostDiscoveryOrchestrator
    ├── models.py                    # [implemented] HostDiscoveryAdapters (the frozen DI bundle
    │                              # of already-bound, zero-argument adapter callables) and
    │                              # HostDiscoverySnapshot (frozen, JSON-serializable, this
    │                              # component's only output type) - both data-holding types,
    │                              # consolidated into one module since neither has execution
    │                              # or coordination logic of its own
    └── orchestrator.py               # [implemented] HostDiscoveryOrchestrator -
                                     # the coordination logic
```

**A structural refinement from this document's original sketch, flagged rather than silently done:** the Public API section below originally proposed `adapters.py`/`snapshot.py` as two separate modules. The actual implementation consolidates both into a single `models.py` — the same "one module per distinct concern" reasoning that split `bcs.platform.adapters.efi` into four files doesn't apply as strongly here, since neither `HostDiscoveryAdapters` nor `HostDiscoverySnapshot` contains any logic (execution, coordination, or otherwise) to keep separate from the other; they are both plain data-holding types. The public import surface (`from bcs.inventory.discovery import HostDiscoveryAdapters, HostDiscoverySnapshot`) is unaffected either way.

Organized as a small subpackage rather than a flat module for the same reason `bcs.platform.adapters.efi` was (see [ADR-0010](decisions/0010-efi-adapter-read-only-scope.md), point 7): three distinct concerns (a DI bundle, an output model, coordination logic) benefit from separation, and the public import surface (`from bcs.inventory.discovery import HostDiscoveryOrchestrator, ...`) is unaffected either way.

**Why `bcs.inventory.discovery`, not `bcs.platform.discovery`:** the Platform Layer is explicitly designed to depend on nothing above it ([docs/PLATFORM_LAYER.md § Purpose](PLATFORM_LAYER.md#purpose): "`CommandRunner` depends on nothing above it"). This component depends on `HostInventory`-adjacent concepts — it exists to feed Host Inventory, and it directly reuses `bcs.inventory.collectors`' existing CPU/Memory/Network functions (see below) — so putting it under `bcs.platform` would invert that dependency direction. Putting it under `bcs.inventory` instead matches a direction [docs/PLATFORM_LAYER.md § Dependency Injection](PLATFORM_LAYER.md#dependency-injection)'s own diagram already anticipated (`Inventory -.optional future dependency.-> Lsblk`, `-.optional future dependency.-> Blkid`) — Host Inventory depending on Platform Layer adapters, never the reverse.

## Dependency Diagram

```mermaid
flowchart TB
    subgraph Discovery["bcs.inventory.discovery — this design"]
        Adapters["discovery.adapters\nHostDiscoveryAdapters"]
        Snapshot["discovery.snapshot\nHostDiscoverySnapshot"]
        Orchestrator["discovery.orchestrator\nHostDiscoveryOrchestrator"]
    end

    subgraph PlatformModels["Platform Layer adapter MODELS only — no execution"]
        EfiModels["platform.adapters.efi.models\nFirmwareBootConfiguration"]
        StorageModels["platform.adapters.storage.models\nBlockDevice, StorageConfiguration"]
        SecureBootModels["platform.adapters.secureboot.models\nSecureBootStatus"]
        FutureModels["future: filesystem / tpm models\n(not designed yet)"]
    end

    subgraph InventoryCore["bcs.inventory — existing"]
        InvModels["inventory.models\nCpuInfo, MemoryInfo, NetworkInterface, HostInventory"]
        Collectors["inventory.collectors\ncollect_cpu, collect_memory, collect_network\n(reused as-is, see § Dependency Injection Strategy)"]
        Service["inventory.service\ncollect_host_inventory()"]
    end

    subgraph NeverImported["Never imported by this design"]
        Execution["platform.execution\nCommandRunner, SubprocessCommandRunner"]
        Subprocess["subprocess (stdlib)"]
    end

    Adapters --> EfiModels
    Adapters --> StorageModels
    Adapters --> SecureBootModels
    Adapters --> FutureModels
    Adapters --> InvModels

    Snapshot --> EfiModels
    Snapshot --> StorageModels
    Snapshot --> SecureBootModels
    Snapshot --> FutureModels
    Snapshot --> InvModels

    Orchestrator --> Adapters
    Orchestrator --> Snapshot

    Service --> Orchestrator
    Service --> Collectors

    Orchestrator -.never imports.-> Execution
    Orchestrator -.never imports.-> Subprocess
```

## Component Diagram

```mermaid
flowchart TB
    subgraph AppStartup["bcs.app.main() — composition root, runs once per invocation"]
        BuildRunner["construct SubprocessCommandRunner()"]
        BuildAdapters["bind each adapter's read_*/collect_* function\nto its dependencies -> HostDiscoveryAdapters"]
        BuildOrchestrator["construct HostDiscoveryOrchestrator(adapters)"]
    end

    subgraph BoundAdapters["Already-bound, zero-argument callables — see § Public API"]
        EfiBound["efi: () -> FirmwareBootConfiguration\n(bound to read_firmware_boot_configuration + command_runner)"]
        StorageBound["storage: () -> StorageConfiguration\n(bound to read_storage_topology + command_runner)"]
        SecureBootBound["secure_boot: () -> SecureBootStatus\n(bound to read_secure_boot_status + command_runner)"]
        CpuBound["cpu: collectors.collect_cpu\n(already zero-arg, no binding needed)"]
        MemoryBound["memory: collectors.collect_memory\n(already zero-arg, no binding needed)"]
        NetworkBound["network: collectors.collect_network\n(already zero-arg, no binding needed)"]
        FutureBound["filesystem / tpm: None\n(no adapter wired in yet)"]
    end

    subgraph Core["bcs.inventory.discovery — this design"]
        Orchestrator["HostDiscoveryOrchestrator.discover()"]
    end

    subgraph Consumers["Consumers"]
        Service["inventory.service.collect_host_inventory(orchestrator)"]
        CLIAdapter["commands.inventory\nbcs inventory"]
        DoctorAdapter["commands.doctor\nbcs doctor (reads one slot directly, see § Sequence Diagram)"]
    end

    BuildRunner --> BuildAdapters
    BuildAdapters --> EfiBound
    BuildAdapters --> StorageBound
    BuildAdapters --> SecureBootBound
    BuildAdapters --> CpuBound
    BuildAdapters --> MemoryBound
    BuildAdapters --> NetworkBound
    BuildAdapters --> FutureBound
    BuildAdapters --> BuildOrchestrator
    BuildOrchestrator --> Orchestrator

    Orchestrator --> EfiBound
    Orchestrator --> StorageBound
    Orchestrator --> SecureBootBound
    Orchestrator --> CpuBound
    Orchestrator --> MemoryBound
    Orchestrator --> NetworkBound

    Service --> Orchestrator
    CLIAdapter --> Service
    DoctorAdapter --> BuildAdapters
```

## Public API

### `HostDiscoveryAdapters` (`discovery/models.py`) — implemented

A frozen `dataclass` (not a Pydantic model — it holds callables, not serializable data). Mirrors [`RuntimeContext`](../cli/src/bcs/context.py)'s own precedent exactly: a frozen bundle of collaborators, built once at the composition root. Every field is **optional** and defaults to `None`, meaning "no adapter wired in for this domain in this build" — never an error by itself; see [§ Error Propagation](#error-propagation).

| Field | Type | Bound to (illustrative) | Status |
|---|---|---|---|
| `efi` | `Callable[[], FirmwareBootConfiguration] \| None` | `functools.partial(read_firmware_boot_configuration, runner=command_runner)` | Adapter implemented ([EFI_ADAPTER.md](EFI_ADAPTER.md)) |
| `storage` | `Callable[[], StorageConfiguration] \| None` | `functools.partial(read_storage_topology, runner=command_runner)` | Adapter fully implemented ([STORAGE_ADAPTER.md](STORAGE_ADAPTER.md)) |
| `secure_boot` | `Callable[[], SecureBootStatus] \| None` | `functools.partial(read_secure_boot_status, runner=command_runner)` | Adapter fully implemented ([SECURE_BOOT_ADAPTER.md](SECURE_BOOT_ADAPTER.md)) and wired at the composition root |
| `filesystem` | `Callable[[], object] \| None` *(type TBD)* | — | Not designed yet — see [§ Future Extensibility](#future-extensibility) for its boundary against `storage` |
| `network` | `Callable[[], list[NetworkInterface]] \| None` | `collectors.collect_network` (already zero-argument, no binding needed) | Existing `sysfs`-based collector, reused as-is |
| `cpu` | `Callable[[], CpuInfo] \| None` | `collectors.collect_cpu` (already zero-argument, no binding needed) | Existing `sysfs`-based collector, reused as-is |
| `memory` | `Callable[[], MemoryInfo] \| None` | `collectors.collect_memory` (already zero-argument, no binding needed) | Existing `sysfs`-based collector, reused as-is |
| `tpm` | `Callable[[], object] \| None` *(type TBD)* | — | Not designed yet, and not currently motivated by any `SPECIFICATION.md` requirement — included because it was named as a target domain, not as a recommendation to build it next; see [§ Future Extensibility](#future-extensibility) |

**Corrected during implementation:** `network` is typed `Callable[[], list[NetworkInterface]]`, not the `tuple[NetworkInterface, ...]` this table originally showed — matching `collectors.collect_network`'s actual, already-implemented return type (`list[NetworkInterface]`, per `bcs.inventory.models.HostInventory`). The original table's claim that this slot needs "no binding needed" was only true with the corrected type; a `tuple`-typed slot would have made that claim false under `mypy --strict`. This project's own architecture review of this document (finding 6) flagged the discrepancy before implementation reached it.

Explicit, named, optional slots — not a dynamic registry keyed by string, and not a `Collector`-style protocol third parties register against. [docs/HOST_INVENTORY.md § Proposed Changes, item 4](HOST_INVENTORY.md#proposed-changes-requiring-approval) already considered and declined a dynamic collector registry, "since there is no concrete second contributor yet... exactly the kind of speculative flexibility [REVIEW.md §7] already argues against." The same reasoning applies here: all eight domains this orchestrator coordinates are already known and named (by this very design brief); a ninth arriving later is a small, reviewed, one-field addition to two data structures, not a runtime extension point.

### `HostDiscoverySnapshot` (`discovery/models.py`) — implemented

A frozen, JSON-serializable Pydantic model — this component's **only** output type. Field-for-field, every payload field mirrors a `HostDiscoveryAdapters` slot exactly: whatever the bound callable returned, unmodified, or absent if that slot was unset or its call failed (see [§ Error Propagation](#error-propagation)). Like `CommandResult`, `FirmwareBootConfiguration`, and `StorageConfiguration`, it deliberately does **not** carry its own `schemaVersion` — it is never a `bcs` command's own top-level payload; it is always consumed by `bcs.inventory.service.collect_host_inventory()` on its way into `HostInventory` (see [§ Relationship to Host Inventory](#relationship-to-host-inventory)).

| Field | JSON alias | Type | Notes |
|---|---|---|---|
| `firmware_boot_configuration` | `firmwareBootConfiguration` | `FirmwareBootConfiguration \| None` | From the `efi` adapter slot. |
| `storage_topology` | `storageTopology` | `StorageConfiguration \| None` | From the `storage` adapter slot. |
| `secure_boot` | `secureBoot` | `SecureBootStatus \| None` | From the `secure_boot` slot; `None` if unset or its call failed. Wired at the composition root. |
| `filesystem` | `filesystem` | *(type TBD)* `\| None` | From the `filesystem` slot; always `None` until that adapter exists. |
| `network` | `network` | `tuple[NetworkInterface, ...]` | From the `network` slot; empty tuple if unset. Kept as `tuple` here (unlike the `list`-typed `HostDiscoveryAdapters.network` slot above) since the snapshot itself must stay immutable; converting `list` to `tuple` is the orchestrator's job. |
| `cpu` | `cpu` | `CpuInfo \| None` | From the `cpu` slot. |
| `memory` | `memory` | `MemoryInfo \| None` | From the `memory` slot. |
| `tpm` | `tpm` | *(type TBD)* `\| None` | From the `tpm` slot; always `None` until that adapter exists. |
| `caveats` | `caveats` | `tuple[str, ...]` | One entry per domain whose adapter was wired in but raised a `PlatformError` when called — see [§ Error Propagation](#error-propagation). Empty tuple if every wired adapter succeeded (or none were wired at all). |

**Hashability, verified during implementation:** a `HostDiscoverySnapshot` is hashable only when `network` is empty. `NetworkInterface` (`bcs.inventory.models`) carries its own `ip_addresses: list[str]` field, and a `list`-typed field is never hashable *by type*, independent of whether it happens to be empty — so any snapshot whose `network` tuple contains at least one `NetworkInterface` raises `TypeError` on `hash()`, matching `HostInventory`'s own already-documented same limitation.

### `HostDiscoveryOrchestrator` (`discovery/orchestrator.py`) — implemented

```
class HostDiscoveryOrchestrator:
    def __init__(self, adapters: HostDiscoveryAdapters) -> None: ...
    def discover(self) -> HostDiscoverySnapshot: ...
```

- A single public method, `discover()`, taking no arguments (everything it needs was already injected via the constructor) and returning a fully-populated `HostDiscoverySnapshot`.
- Not a `Protocol` with multiple implementations, unlike `CommandRunner`: there is exactly one coordination strategy (call every wired slot, isolate failures, aggregate), and the test seam is the *adapters bundle* it is constructed with, not the orchestrator class itself — see [§ Testing Strategy](#testing-strategy).
- `discover()` is expected to be called at most once per `bcs` invocation, mirroring `collect_host_inventory()`'s own current usage; nothing prevents calling it more than once (each call re-invokes every wired adapter and produces a fresh, independent snapshot, matching Host Inventory's own "immutable snapshot, re-collected whenever fresh data is needed" principle), but no current consumer needs to.
- Internally, each domain is called through a small private helper (`_call_adapter`, a `[T]`-generic function, not a loop over a dict of field names) that returns `None` for an unset slot, isolates a `PlatformError` into one `caveats` entry, and lets any other exception propagate — implementing exactly the contract in [§ Error Propagation](#error-propagation). Domains are visited in the fixed order `efi`, `storage`, `secure_boot`, `filesystem`, `network`, `cpu`, `memory`, `tpm`, matching `HostDiscoveryAdapters`' own field order; an unexpected exception halts that order immediately, so domains after the failing one are never called for that `discover()` invocation.

## Dependency Injection Strategy — implemented

Follows the same seam every other Platform Layer/Host Inventory collaborator already uses ([docs/PLATFORM_LAYER.md § Dependency Injection](PLATFORM_LAYER.md#dependency-injection)):

1. **`bcs.app.main()`, the composition root, and nowhere else, constructs `HostDiscoveryAdapters`.** It is the one place that knows how to bind each adapter's real function to its dependencies — `functools.partial(read_firmware_boot_configuration, runner=command_runner)` for `efi`, `functools.partial(read_storage_topology, runner=command_runner)` for `storage`, `functools.partial(read_secure_boot_status, runner=command_runner)` for `secure_boot`, a direct reference (`collectors.collect_cpu`/`collect_memory`/`collect_network`) for the three slots that are already zero-argument, and `None` for every domain with no `adapter.py` at all (`filesystem`/`tpm`, neither designed yet). Built exactly once per invocation, at the same point `SubprocessCommandRunner` itself is built, and reused for the rest of that invocation - never constructed lazily per adapter slot.
2. **`HostDiscoveryOrchestrator` receives `HostDiscoveryAdapters` as a constructor argument** — never constructs one itself, never imports an adapter module directly, and never reaches for a module-level default.
3. **`HostDiscoveryOrchestrator` never sees a `CommandRunner`.** By the time it receives `HostDiscoveryAdapters`, every slot that needed one has already been bound to it upstream. This is what makes "depend only on adapter interfaces" a literal, checkable property rather than just an intent: `discovery/orchestrator.py` and `discovery/models.py` have no import of `bcs.platform.execution` or `subprocess` to check for — verified mechanically, not just by convention, via an AST-based purity test in each module's own test file (mirroring the same technique already established for the EFI/Storage parsers) — the same mechanical guarantee [docs/PLATFORM_LAYER.md § Enforcement](PLATFORM_LAYER.md#enforcement) already established for `bcs.platform.execution` itself, extended here by omission rather than by an explicit Ruff scoping rule (there is no legitimate reason this package would ever import `subprocess`, so there is nothing to scope an ignore for).
4. **Testing substitutes a `HostDiscoveryAdapters` built from stub callables** (plain lambdas or functions returning a canned model or raising a canned `PlatformError` subclass) — no `FakeCommandRunner`, no mocking of any adapter's internals, no monkeypatching. See [§ Testing Strategy](#testing-strategy).

This mirrors, one layer up, [docs/PLATFORM_LAYER.md § Design Principles](PLATFORM_LAYER.md#design-principles) item 5's own statement for `CommandRunner`: "consumed via dependency injection... so tests substitute a fake without patching module state."

## Lifecycle — implemented

- **Who constructs `HostDiscoveryAdapters` and `HostDiscoveryOrchestrator`:** `bcs.app.main()`, at the same point in startup `SubprocessCommandRunner` is already built (per [docs/PLATFORM_LAYER.md § Ownership and Lifecycle](PLATFORM_LAYER.md#ownership-and-lifecycle)) — no other module instantiates either.
- **When:** once per `bcs` process invocation, after `command_runner` is available (several `HostDiscoveryAdapters` slots depend on it) and before any subcommand runs.
- **Who owns it:** `RuntimeContext.host_discovery_orchestrator: HostDiscoveryOrchestrator`, exactly the treatment already given to `command_runner` — a real, additive field on `RuntimeContext`'s frozen dataclass; see [§ Relationship to Host Inventory](#relationship-to-host-inventory---implemented) for why this is a necessary, not optional, consequence of this design. Because `RuntimeContext` is frozen, this reference is fixed for the lifetime of the invocation, matching every other collaborator on it.
- **How consumers obtain it:** as an explicit constructor/function parameter, threaded down from `RuntimeContext` — never a module-level global, never a service locator. `bcs.commands.inventory.run_inventory(runtime)` already receives `RuntimeContext` and could pass `runtime.host_discovery_orchestrator` to `collect_host_inventory()` — that specific call site is not yet updated to do so (see this document's own status banner); the orchestrator is built and available on every `RuntimeContext` today, but no command consumes it yet.
- **Does it hold state across calls?** No. `HostDiscoveryOrchestrator` itself is stateless beyond the `HostDiscoveryAdapters` it was constructed with; each `discover()` call is an independent, fresh sweep — there is no cache, no "last known snapshot," matching [docs/HOST_INVENTORY.md § Design Principles](HOST_INVENTORY.md#design-principles) item 2: "a change in the machine's state produces a *new* snapshot, not an update to an old one."

## Relationship to Host Inventory — implemented

`bcs.inventory.service.collect_host_inventory()` ([`service.py`](../cli/src/bcs/inventory/service.py)) gained an `orchestrator: HostDiscoveryOrchestrator | None = None` parameter, defaulting to `None`:

1. **`orchestrator=None` (the default):** behaviour is byte-for-byte identical to before this parameter existed — `cpu`, `memory`, and `network` all come from `collectors.collect_cpu()`/`collect_memory()`/`collect_network()` exactly as before.
2. **`orchestrator` given:** `orchestrator.discover()` is called exactly once, to get a `HostDiscoverySnapshot`.
3. Continues to call `collectors.collect_identity()` and `collectors.collect_tooling()` directly regardless — these two fact areas have no Discovery adapter equivalent named in this design's scope (identity and tooling presence are not among the eight orchestrated domains) and are unaffected either way.
4. Assembles `HostInventory` from both: `collected_at`, `identity`, `firmware`, `operating_system`, `efi_system_partition`, `storage`/`usb_storage`, and `tooling` continue to come from the *existing* collectors unconditionally; `network` is satisfied from the snapshot (`list(snapshot.network)`, an empty list if that slot was unset — a valid value, since `HostInventory.network` already defaults to `[]`).
5. **Refinement beyond this section's original wording, flagged rather than silently done:** `cpu`/`memory` are **not** taken from the snapshot unconditionally. `HostDiscoverySnapshot.cpu`/`memory` are `Optional` (`None` when that slot is unset, or when its adapter raised a `PlatformError` — see [§ Error Propagation](#error-propagation)), but `HostInventory.cpu`/`memory` are *required* fields with no `None` variant; passing a `None` snapshot value straight through would raise a Pydantic `ValidationError`, which is not "preserve all existing inventory behaviour." `collect_host_inventory()` instead falls back to the same `collectors.collect_cpu()`/`collect_memory()` call it would have made without an orchestrator at all, whenever the snapshot's value is `None`:
   ```python
   cpu = snapshot.cpu if snapshot.cpu is not None else collectors.collect_cpu()
   memory = snapshot.memory if snapshot.memory is not None else collectors.collect_memory()
   ```
   `network` needs no equivalent fallback, since an empty list is already a valid `HostInventory.network` value.
6. **This integration does not add `firmwareBootConfiguration`/`storageTopology`/etc. as new `HostInventory` fields.** Doing so is an additive `HostInventory` schema change — the same category of change [ADR-0008](decisions/0008-host-inventory-ports-and-adapters.md)'s own EFI System Partition/USB Storage amendment already made once — and remains a **separate, explicitly flagged follow-up**, per [ADR-0011](decisions/0011-host-discovery-orchestrator.md) Decision point 6 and Consequences: this integration's job was wiring the orchestrator into `collect_host_inventory()`, not a rewrite of `docs/HOST_INVENTORY.md`'s schema. `HostDiscoverySnapshot.firmware_boot_configuration`/`storage_topology`/`secure_boot`/`filesystem`/`tpm`/`caveats` remain available to any caller of `orchestrator.discover()` directly, but do not appear in `bcs inventory`'s own JSON output.
7. **No duplicated error handling.** No `try`/`except` wraps `orchestrator.discover()` — any exception it raises (which, by [§ Error Propagation](#error-propagation)'s own contract, can only be a non-`PlatformError`, since `PlatformError` is already isolated inside `discover()` into `caveats`) propagates out of `collect_host_inventory()` completely unmodified, exactly as none of the existing collector calls are wrapped either.

This sequencing deliberately mirrors how `RuntimeContext.command_runner` shipped (Platform-001 Part 4) before any collector was migrated to use it: dependency injection wiring first, `RuntimeContext`/CLI-command migration as an explicit, separate, later step (still not yet done — see this document's status banner).

## Sequence Diagram

### `bcs inventory --output json`, once this design and its `HostInventory` follow-up both land (illustrative)

```mermaid
sequenceDiagram
    actor Tech as Technician
    participant CLI as commands.inventory
    participant Svc as inventory.service
    participant Orch as discovery.HostDiscoveryOrchestrator
    participant EfiAdapter as (bound) efi slot
    participant StorageAdapter as (bound) storage slot
    participant Cpu as (bound) cpu slot
    participant Col as inventory.collectors

    Tech->>CLI: bcs inventory --output json
    CLI->>Svc: collect_host_inventory(runtime.host_discovery_orchestrator)
    Svc->>Orch: discover()
    Orch->>EfiAdapter: call()
    EfiAdapter-->>Orch: FirmwareBootConfiguration
    Orch->>StorageAdapter: call()
    StorageAdapter--xOrch: raises a PlatformError subclass
    Orch->>Cpu: call()
    Cpu-->>Orch: CpuInfo
    Orch-->>Svc: HostDiscoverySnapshot(..., caveats=("storage: StorageUnavailableError: ...",))
    Svc->>Col: collect_identity(), collect_tooling()
    Col-->>Svc: HostIdentity, list~ToolStatus~
    Svc-->>CLI: HostInventory
    CLI-->>Tech: stdout: JSON
```

### `bcs doctor --check secure-boot` (selective path, illustrative — mirrors the existing `doctor` asymmetry)

```mermaid
sequenceDiagram
    actor Tech as Technician
    participant Cmd as commands.doctor
    participant Adapters as discovery.HostDiscoveryAdapters

    Tech->>Cmd: bcs doctor --check secure-boot
    Cmd->>Adapters: read secure_boot
    alt slot is None
        Adapters-->>Cmd: None
        Cmd-->>Tech: "[ SKIP ] secure-boot   no adapter available"
    else slot is bound
        Adapters-->>Cmd: bound callable
        Cmd->>Cmd: call it, catch PlatformError itself
        Cmd-->>Tech: "[ OK / WARN / FAIL ] secure-boot   ..."
    end
```

This preserves [docs/HOST_INVENTORY.md § Dependency Graph](HOST_INVENTORY.md#dependency-graph)'s existing, deliberate asymmetry — `doctor` evaluates one fact at a time and must not pay for, or be blocked by, an unrelated check — by having `doctor` read one named slot off `HostDiscoveryAdapters` directly, rather than calling `HostDiscoveryOrchestrator.discover()`'s full sweep for a single check.

## Error Propagation

**Implemented exactly as designed.** For each non-`None` slot in `HostDiscoveryAdapters`, `discover()`:

1. **Calls it.**
2. **On success,** stores the returned model directly on the matching `HostDiscoverySnapshot` field, unmodified.
3. **On a raised `bcs.platform.errors.PlatformError`** (or any subclass — `FirmwareBootError`, a future `StorageError`, a future `SecureBootError`, etc.), leaves that field `None` and appends one entry to `caveats` (e.g. `"efi: FirmwareBootUnavailableError: ..."`) — logged at `WARNING`, matching [docs/PLATFORM_LAYER.md § Logging Strategy](PLATFORM_LAYER.md#logging-strategy)'s existing "logged in addition to, not instead of, raising" convention, adapted here to "logged in addition to, not instead of, isolating." **One domain's failure never prevents the other seven from being collected** — the same per-unit failure isolation [`NFR-001`](../SPECIFICATION.md#3-non-functional-requirements) already requires of Deploy's per-machine handling and `bcs doctor`'s own per-check independence, applied one layer down to per-*domain* discovery.
4. **On any other exception** (not a `PlatformError` — e.g. a `TypeError` from a miswired callable), the exception **propagates unmodified out of `discover()`**. This is a genuine bug, not a "this environment doesn't have Secure Boot" fact, and per [docs/standards/coding-standards.md § Error Handling](standards/coding-standards.md#error-handling), "don't swallow errors to make output quieter" — the orchestrator is disciplined about *which* failures are expected (typed, adapter-declared `PlatformError`s) and refuses to guess about the rest.
5. **For a `None` slot** (no adapter wired for that domain), the matching field is simply `None`/empty with **no `caveats` entry** — this is a configuration fact ("this build of `bcs` doesn't have this adapter wired in"), not a runtime failure, and conflating the two would make `caveats` noisy on every single invocation for domains that are permanently unwired today (`filesystem`, `tpm`). A wired `secure_boot` adapter raising a `PlatformError` (e.g. `mokutil` not found) *does* get a `caveats` entry, exactly like `efi`/`storage`.

**`caveats` is a direct, narrower realization of [docs/HOST_INVENTORY.md § Proposed Changes, item 1](HOST_INVENTORY.md#proposed-changes-requiring-approval)** ("a `None`/empty value from a collector is ambiguous... add a `caveats: list[str]` field"), scoped to this orchestrator's own output rather than to `HostInventory` directly. Approving `HostDiscoverySnapshot.caveats` here does not, by itself, approve adding an equivalent field to `HostInventory` itself or to any already-accepted section of it — that remains its own, separately approvable follow-up, per this project's usual granular-approval convention (see, e.g., how accepting [ADR-0008](decisions/0008-host-inventory-ports-and-adapters.md) did not itself approve every item in [docs/HOST_INVENTORY.md § Proposed Changes Requiring Approval](HOST_INVENTORY.md#proposed-changes-requiring-approval)).

## Testing Strategy

| Layer | What it verifies | How |
|---|---|---|
| `HostDiscoveryAdapters` **(implemented)** | Construction, defaults (every slot `None`), all slots bound, frozen (assignment raises), equality, hashability (a frozen dataclass of `Callable \| None` fields hashes by reference, unaffected by what a bound callable would return if called). | Direct unit tests, no fixtures — see `cli/tests/test_inventory_discovery_models.py`. |
| `HostDiscoverySnapshot` **(implemented)** | Construction, defaults, `populate_by_name` aliases, frozen/extra-forbid, a concrete `SecureBootStatus`-typed `secure_boot` value and opaque `object`-typed `filesystem`/`tpm` values, equality, JSON round-tripping (including nested models), and hashability's actual, verified boundary: hashable whenever `network` is empty; raises `TypeError` whenever it contains at least one `NetworkInterface`, since that model's own `ip_addresses: list[str]` field is never hashable *by type* regardless of content — corrected from this table's own earlier, untested claim that an empty-`ip_addresses` interface would hash cleanly. | Direct unit tests, mirroring `test_platform_adapters_efi_models.py`/`test_platform_adapters_storage_models.py`'s own style exactly — no fixtures, no mocking. `discovery/models.py` is at 100% statement and branch coverage. |
| `HostDiscoveryOrchestrator.discover()` **(implemented)** | No adapters configured; one/several/all configured; every slot populated → every `HostDiscoverySnapshot` field populated in the declared order; every slot `None` → every field absent/empty and `caveats` empty (no caveat for an unset slot); a slot's callable raising `PlatformError` (base class and a subclass both) → that field `None`, one matching `caveats` entry, *and* every other slot still populated (the isolation property, [§ Error Propagation](#error-propagation) point 3); multiple failing slots → one caveat each, in order; a slot's callable raising a non-`PlatformError` → propagates out of `discover()` uncaught, unwrapped (same exception instance), and halts before any later slot is called; every configured adapter called exactly once per `discover()` call; calling `discover()` twice re-invokes every wired adapter a second time; the `network` slot's `list` result is converted to a `tuple` on the snapshot, and stays `()` (never `None`) even when that slot fails. | `HostDiscoveryAdapters` built entirely from lightweight fake callables (a small generic `_CountingAdapter[T]` recording call counts, plus plain functions for the execution-order test) — no `FakeCommandRunner`, no real adapter, no mocking of anything. See `cli/tests/test_inventory_discovery_orchestrator.py`; `discovery/orchestrator.py` is at 100% statement and branch coverage. This is the main coverage burden for this component, and it needs none of the machinery any individual adapter's own tests need. |
| Composition-root wiring (`bcs.app.main()` → `RuntimeContext.host_discovery_orchestrator`) **(implemented)** | `HostDiscoveryOrchestrator` and `HostDiscoveryAdapters` are each constructed exactly once per invocation (never lazily, never re-built per adapter slot access); two separate invocations get two distinct instances (no module-level singleton/service locator); the `efi`/`storage`/`secure_boot` slots' `functools.partial` bindings share the exact same `CommandRunner` instance `RuntimeContext.command_runner` carries; `network`/`cpu`/`memory` are bound directly to `bcs.inventory.collectors`' own functions, with no `functools.partial` needed; `filesystem`/`tpm` stay unset (no `adapter.py` exists for either of them yet); `RuntimeContext` exposes the exact same orchestrator instance `bcs.app.main()` built - not a copy, not a re-wrapped equivalent; observable CLI command behaviour is unchanged. | CliRunner-level integration tests mirroring `tests/test_command_runner_wiring.py`'s own approach exactly (`monkeypatch` capturing/counting wrappers around `HostDiscoveryAdapters`/`HostDiscoveryOrchestrator`/`RuntimeContext` at the `bcs.app` module level, never mocking an adapter's internals) plus a small `RuntimeContext`-level identity/exposure section mirroring the existing `command_runner` tests. See `cli/tests/test_host_discovery_wiring.py` and the "Host Discovery Orchestrator Part 4" section of `cli/tests/test_context.py`. |
| `bcs.inventory.service.collect_host_inventory(orchestrator)` **(implemented)** | `orchestrator=None`/omitted behaves identically to before the parameter existed; a given orchestrator supplies `cpu`/`memory`/`network` instead of the direct collector calls; every other section unaffected; the orchestrator is called exactly once; a snapshot's `None` `cpu`/`memory` (unset slot, or an isolated `PlatformError`) falls back to the matching collector; `network` stays `[]` with no fallback call when unset; an unexpected exception from `orchestrator.discover()` propagates out unmodified. | `monkeypatch`-based fakes for the non-discovery collectors (matching the existing test style, per [docs/HOST_INVENTORY.md § Testing Strategy](HOST_INVENTORY.md#testing-strategy)), plus real `HostDiscoveryOrchestrator`/`HostDiscoveryAdapters` instances built from stub callables (including a `_CountingAdapter[T]`, mirroring the orchestrator's own test fixture) — no `FakeCommandRunner`, no mocking. See `cli/tests/test_inventory_service.py`; the new logic is at 100% statement and branch coverage. |
| Full pipeline, end to end **(implemented)** | The complete path — `bcs.app.main()`'s composition root, `RuntimeContext.host_discovery_orchestrator`, `HostDiscoveryAdapters` binding the *real, currently-implemented* `efi`/`storage`/`secure_boot` adapters (not lightweight fakes) to one shared `CommandRunner`, `HostDiscoveryOrchestrator.discover()`, and the resulting `HostDiscoverySnapshot` — works together correctly: every tool-based adapter invoked exactly once per `discover()` call; the locale-forced environment reaches every adapter; a `PlatformError` from one real adapter (a missing executable, or a recognizable "environment cannot provide this data" `stderr`) isolates into exactly one `caveats` entry in the exact `"{domain}: {ExceptionType}: {message}"` format, naming that adapter's own actual exception subclass, while every other domain still succeeds; multiple independent failures each get their own caveat, in field order. | A single, shared, multi-tool `FakeCommandRunner` (keyed by `command[0]`, mirroring `test_platform_adapters_storage_adapter.py`'s own fake) binds all three real adapter functions via the exact same `functools.partial` shape `bcs.app.main()` uses; one test builds the orchestrator directly, another patches only `SubprocessCommandRunner` and drives it through a real CLI invocation via `CliRunner`/`bcs.app.main()`, capturing the exact `HostDiscoveryOrchestrator` instance the composition root built. `network`/`cpu`/`memory` use the real, unfaked `bcs.inventory.collectors` functions throughout, exactly as production does. See `cli/tests/test_host_discovery_pipeline.py`. |

## Future Extensibility

- **Adding Filesystem or TPM once each has its own accepted adapter design** (Secure Boot already went through this exact process — see [docs/SECURE_BOOT_ADAPTER.md](SECURE_BOOT_ADAPTER.md) and the `secure_boot` rows throughout this document): add one new field to `HostDiscoveryAdapters` and one to `HostDiscoverySnapshot`, bind it at the composition root, done — `HostDiscoveryOrchestrator`'s own coordination logic needs no change (it already iterates its full, fixed field set). This is the concrete payoff of the explicit-slots design over a dynamic registry: each addition is a small, reviewable diff against two data structures, not a runtime extension mechanism to design and secure.
- **Replacing the `network`/`cpu`/`memory` slots' current `sysfs`-based bindings with future tool-based adapters** (e.g. an `ip`-based Network adapter closing [docs/HOST_INVENTORY.md](HOST_INVENTORY.md#open-questions--explicitly-deferred)'s own documented `ip_addresses` gap) — only the composition root's binding changes; a slot's declared type may need to widen (e.g. `network`'s type becoming a new, richer model rather than `tuple[NetworkInterface, ...]`), a normal, expected, one-field consequence of that adapter's own future design, not a redesign of this orchestrator.
- **The `filesystem` domain's boundary against the Storage Adapter's already-designed `FilesystemInfo`/`MountEntry`** is not resolved by this document itself, but is now resolved by [docs/FILESYSTEM_ADAPTER.md § Relationship to the Storage Adapter](FILESYSTEM_ADAPTER.md#relationship-to-the-storage-adapter) (`Proposed`, pending approval): a distinct domain (topology vs. usage), not an enrichment of `FilesystemInfo`. The `filesystem` slot stays unfilled here until that design is accepted and implemented — this document's own coordination logic does not change either way.
- **A future `HostInventory` schema amendment** (see [§ Relationship to Host Inventory](#relationship-to-host-inventory---implemented), point 6) is the natural next step once this design is accepted, but is out of scope here by design.
- **A future REST API or Web UI** (per [docs/HOST_INVENTORY.md § Interaction with a Future REST API](HOST_INVENTORY.md#interaction-with-a-future-rest-api)) is unaffected: it would still call `collect_host_inventory(orchestrator)` (or, eventually, receive `orchestrator` via its own DI container) exactly as `bcs inventory` does — nothing about this design is CLI-specific.
- **Parallelizing the up-to-eight adapter calls** within `discover()` (they are independent of each other) is a plausible future performance optimization, not designed or recommended here — today's two implemented/designed adapters make this premature; see [§ Open Questions](#open-questions).

## Open Questions

- **Exact `HostInventory` schema amendment** (new field names; whether `EfiSystemPartition`/`StorageDevice`/`FirmwareInfo` are ever reconciled with `StorageConfiguration`/`FirmwareBootConfiguration`) — deliberately deferred; see [§ Relationship to Host Inventory](#relationship-to-host-inventory---implemented), point 6.
- **Retry/timeout composition across multiple adapter calls within one `discover()` sweep** — each adapter already enforces its own `timeout_seconds` (per [docs/PLATFORM_LAYER.md § Timeout Handling](PLATFORM_LAYER.md#timeout-handling)); whether `discover()` itself needs an aggregate budget (relevant once several tool-based adapters are wired at once) is not designed here.
- **Parallelizing the up-to-eight adapter calls** within `discover()` — see [§ Future Extensibility](#future-extensibility); not designed or recommended now.

## Related Documents

- [docs/decisions/0011-host-discovery-orchestrator.md](decisions/0011-host-discovery-orchestrator.md) — the architectural decision this design proposal builds on (status: `Accepted`).
- [docs/PLATFORM_LAYER.md § Open Questions](PLATFORM_LAYER.md#open-questions--explicitly-deferred) — the deferred `CommandRunner` migration question this document resolves.
- [docs/EFI_ADAPTER.md § Open Questions](EFI_ADAPTER.md#open-questions) and [docs/STORAGE_ADAPTER.md § Relationship to Existing Inventory Collectors](STORAGE_ADAPTER.md#relationship-to-existing-inventory-collectors) — the two independently-asked "what exposes this to `HostInventory`" questions this document answers once.
- [docs/HOST_INVENTORY.md](HOST_INVENTORY.md) and [ADR-0008](decisions/0008-host-inventory-ports-and-adapters.md) — the aggregate root and ports-and-adapters discipline this design extends, and the source of the `caveats` idea this design gives a first, narrower home to.
- [docs/standards/naming-conventions.md § Domain-Driven Naming](standards/naming-conventions.md#domain-driven-naming) — `HostDiscoveryOrchestrator`/`HostDiscoveryAdapters`/`HostDiscoverySnapshot` name the coordination concern itself, not any tool or adapter behind it.
- [REVIEW.md §7](../REVIEW.md#7-a-meta-concern-proportionality) — the proportionality concern this document defers to when declining to design a dynamic adapter registry, parallel adapter execution, or the `HostInventory` schema amendment now.
