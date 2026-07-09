# Known Limitations — `bcs` CLI, Phase 0

This document records limitations and gaps in the current implementation. These are **known, accepted, and tracked** — not bugs to be surprised by. Each item links to its owning design document, ADR, or issue for detail.

## `bcs doctor`'s `esp`/`usb-storage` Checks Have No Adapter Equivalent

**Severity:** Low — narrowed from Medium now that `bcs doctor`'s Secure Boot, Storage, and Network checks all read their adapters directly (Beta M4, Host Discovery Orchestrator completion pass)

The `HostDiscoveryOrchestrator` is fully implemented, wired into `RuntimeContext` at the composition root, and test-verified end to end. `bcs inventory` passes `runtime.host_discovery_orchestrator` into `collect_host_inventory()`, which sources `cpu`/`memory`/`network`/`storage`/`firmware.secure_boot` from the Discovery snapshot (falling back to the legacy collector per-field when a slot is unwired or its adapter raised a `PlatformError`). `bcs doctor`'s `secure-boot`, `storage`, and `network` checks also now report real state — each via a **direct** call to its own adapter (`read_secure_boot_status`/`read_storage_topology`/`read_network_interfaces`, all via `runtime.command_runner`), never `runtime.host_discovery_orchestrator.discover()`, per [ADR-0011 § Alternatives Considered](decisions/0011-host-discovery-orchestrator.md#alternatives-considered)'s explicit rejection of a full-sweep orchestrator for `bcs doctor` (see `docs/SECURE_BOOT_IMPLEMENTATION_PLAN.md`). `bcs doctor`'s `esp` and `usb-storage` checks are the two genuine remaining gaps: the Storage Adapter's `BlockDevice`/`Partition` models carry the raw data (GPT partition-type GUID, mount point, `is_removable`) these checks would need, but deriving "this is the ESP" or "this is USB storage" from that raw data is new interpretive business logic the Storage Adapter's own design deliberately declines to provide ("identifying what a given type GUID means is a domain service's responsibility, not this adapter's") - not a translate-or-fallback swap, so it is out of scope here.

**Impact:** `bcs doctor --check esp`/`--check usb-storage` still evaluate `collect_efi_system_partition()`/`collect_usb_storage()` directly, unaffected by the Storage Adapter's presence. Adapter-sourced facts outside `HostInventory`'s existing schema (`firmware_boot_configuration`, and `secure_boot`'s own `setup_mode`/`raw_text`) are collected but never reach any command output — a separate limitation, tracked below under "Host Inventory Schema Does Not Include Discovery-Domain Facts".

**Resolved real-world symptoms:** the first real-world validation run (Ubuntu 24.04, VirtualBox, SATA disk — see `docs/REAL_WORLD_VALIDATION.md`) showed `bcs inventory` reporting `storage: []` on a machine where `lsblk` correctly enumerated `/dev/sda` and its partitions. Root cause: `collect_storage()` (`cli/src/bcs/inventory/collectors.py`) intentionally enumerates only `/dev/nvme*` (per `PLAT-005`), while the Storage Adapter enumerates every device `lsblk` reports. `bcs inventory` now translates and reports the Storage Adapter's output when the orchestrator's `storage` slot is available, resolving this specific symptom; `bcs doctor --check storage` now reports the same, real data. `NetworkInterface.ip_addresses` was a permanent placeholder gap in `bcs inventory` output — `collect_network()` never populated it (pure-stdlib IP discovery wasn't in scope); both `bcs inventory` and `bcs doctor --check network` now report the Network Adapter's `ip -json addr show` data (Beta M3, then the Host Discovery Orchestrator completion pass). `FirmwareInfo.secure_boot` reported `unknown` under UEFI unconditionally — `_read_secure_boot_state()` never actually read the `SecureBoot` EFI variable; `bcs inventory`/`bcs doctor` both now report the real state via the Secure Boot Adapter (Beta M4). Re-validation on the same VM belongs in `docs/VM_TEST_LOG.md` as a new entry, not as an edit to `docs/REAL_WORLD_VALIDATION.md` (a fixed historical record by its own stated policy).

**Tracking:** `docs/HOST_DISCOVERY_ORCHESTRATOR.md` status banner; `docs/IMPLEMENTATION_STATUS.md §8` Outstanding Work; `docs/ISSUE_70_IMPLEMENTATION_CHECKLIST.md`; `docs/SECURE_BOOT_IMPLEMENTATION_PLAN.md`; `docs/BETA_ROADMAP.md` (Milestones M3/M4); issue [#70](https://github.com/nino79/batoi-classroom-suite/issues/70) (`bcs inventory` storage — done) and issue [#78](https://github.com/nino79/batoi-classroom-suite/issues/78) (the full legacy-collector deprecation arc `esp`/`usb-storage` fit into).

## 7 Stub Commands

**Severity:** Medium — by design per MVP scope

`build`, `install`, `deploy`, `backup`, `restore`, `update`, `config` are registered in the command tree so `bcs --help` reflects the full planned surface. Each is a stub that prints "not implemented in this phase" and exits non-zero. No Boot Manager, Builder, or Deploy logic exists in this package.

**Impact:** The CLI is not usable for its ultimate purpose yet.

**Tracking:** Phases 1-3 on `ROADMAP.md`.

## Host Inventory Schema Does Not Include the Full Discovery-Domain Facts

**Severity:** Medium — planned enhancement

`firmware_boot_configuration` and `filesystem_usage` live on `HostDiscoverySnapshot` but are never folded into `HostInventory`'s own schema — no new field exists for either. Per ADR-0011 Decision point 6, adding one requires a separate ADR-0008 amendment. (`storage_topology`'s and `secure_boot`'s own *richer* shapes — partitions/mounts/vendor/serial, and `setup_mode`/`raw_text` respectively — are in the same position; only their narrower, already-existing-field equivalents (`storage`, `firmware.secure_boot`) are populated, via translation, not by adding a new field — see issue #70/Beta M3/Beta M4.)

**Impact:** `bcs inventory --output json` does not include UEFI boot entries or detailed filesystem usage from the tool-based adapters, and does not include the richer storage/Secure Boot facts (partition tables, Setup Mode) beyond what `storage`/`firmware.secureBoot` already expose.

**Tracking:** ADR-0011 Decision point 6.

## Fixtures Corpora are Placeholders

**Severity:** Low — no functional impact

Every fixture file under `cli/tests/fixtures/{firmware,storage,secureboot,network}/` is a zero-byte placeholder. The `filesystem/` directory has no placeholder files at all. No real hardware/VM output has been captured yet.

**Impact:** Parser/adapter tests use synthetic or inline text rather than real captured tool output. This means parser robustness against real-world output variations is untested.

**Tracking:** Each adapter's design document (Fixtures Strategy section).

## Missing `FakeCommandRunner` Test Double

**Severity:** Low — each adapter rolls its own

There is no shared `FakeCommandRunner` under `cli/tests/`. Each adapter test (EFI, Storage, Secure Boot, Filesystem, Network) defines its own `FakeCommandRunner` stand-in, keyed by tool name.

**Impact:** Code duplication across adapter test suites.

**Tracking:** `docs/PLATFORM_LAYER.md § Approved Design Decisions`, item 4.

## Ruff `S603`/`S607` Scoping Not Narrowed

**Severity:** Low — no risk

`cli/pyproject.toml` disables `S603`/`S607` globally rather than scoping to `bcs.plugins` and `bcs.platform.execution` only, per the original Platform Layer design. This means Bandit's `subprocess`-without-`shell=True` warnings are suppressed everywhere, not just in the two modules that legitimately call `subprocess.run()`.

**Impact:** A new module calling `subprocess` outside the Platform Layer would not get a Bandit warning.

**Tracking:** `docs/PLATFORM_LAYER.md § Approved Design Decisions`, item 3.

## No CPU/Memory/TPM Tool-Based Adapters

**Severity:** Low — current collectors suffice for MVP

CPU, Memory, and TPM facts are collected through existing `bcs.inventory.collectors` functions (reading `/proc/cpuinfo`, `/proc/meminfo`, etc.) rather than through Platform Layer adapters. No tool-based adapter is designed or implemented for any of these domains. TPM has no requirements motivating it.

**Impact:** These facts skip the `CommandRunner` abstraction and cannot benefit from its timeout/locale/error machinery.

**Tracking:** `docs/HOST_DISCOVERY_ORCHESTRATOR.md § Future Extensibility`.

## No TPM Adapter Exists

**Severity:** Low — no requirement currently motivates one

The `HostDiscoveryAdapters` and `HostDiscoverySnapshot` types reserve a `tpm` slot name, but no adapter exists for it. `HostDiscoveryOrchestrator.discover()` always leaves `HostDiscoverySnapshot.tpm` as `None`. No design document, ADR, or SPECIFICATION.md requirement currently proposes one.

**Impact:** The `tpm` domain is always absent from discovery snapshots and will never appear in any command output. Adding it later requires an adapter design document, an adapter implementation, and composition-root wiring — exactly the process in `docs/PATTERNS.md`.

**Tracking:** `docs/HOST_DISCOVERY_ORCHESTRATOR.md § Future Extensibility`.

## `FrozenModel`/`FrozenExtensibleModel` Not Relocated

**Severity:** Low — cosmetic

The `FrozenModel`/`FrozenExtensibleModel` base classes (defined in `bcs.config.models` and replicated in `bcs.inventory.models`) have not been consolidated into `bcs.model_utils`.

**Impact:** Two copies of nearly identical Pydantic base classes.

**Tracking:** `docs/PLATFORM_LAYER.md § Approved Design Decisions`, item 5.

## CLI.md References Stale Implementation Status

**Severity:** Informational — design doc not updated

`docs/CLI.md` line 98 still refers to ADR-0009 as "(Accepted, not yet implemented)" — the Platform Layer is fully implemented (Parts 1-4). This is a documentation staleness issue in the design document.

**Note:** This document (`docs/CLI.md`) is a technical design document and is not being updated in this pass per project conventions. See the CLI design document itself for authoritative design; see `docs/IMPLEMENTATION_STATUS.md` for current implementation state.
