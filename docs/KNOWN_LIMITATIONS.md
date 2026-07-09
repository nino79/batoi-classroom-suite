# Known Limitations — `bcs` CLI, Phase 0

This document records limitations and gaps in the current implementation. These are **known, accepted, and tracked** — not bugs to be surprised by. Each item links to its owning design document, ADR, or issue for detail.

## Host Discovery Orchestrator Not Consumed by `bcs doctor`

**Severity:** Medium — narrowed from High now that `bcs inventory` consumes it (issue [#70](https://github.com/nino79/batoi-classroom-suite/issues/70))

The `HostDiscoveryOrchestrator` is fully implemented, wired into `RuntimeContext` at the composition root, and test-verified end to end. `bcs inventory` now passes `runtime.host_discovery_orchestrator` into `collect_host_inventory()`, which sources `cpu`/`memory`/`network`/`storage` from the Discovery snapshot (falling back to the legacy collector per-field when a slot is unwired or its adapter raised a `PlatformError`). `bcs doctor` still sources every fact from the original `bcs.inventory.collectors` directly — it is out of scope for issue #70/Beta M3 (see `docs/ISSUE_70_IMPLEMENTATION_CHECKLIST.md` § 7) because its `storage`/`esp`/`network` checks call collectors directly rather than going through `collect_host_inventory()` (see `docs/HOST_INVENTORY.md`); `_check_network()` (`cli/src/bcs/commands/doctor.py`) specifically still calls `collect_network()` directly, so `bcs doctor --check network` does not benefit from the Network Adapter's `ip_addresses` data either.

**Impact:** Adapter-sourced facts outside `HostInventory`'s existing schema (`firmware_boot_configuration`, `secure_boot`) are collected but never reach any command output — a separate limitation, tracked below under "Host Inventory Schema Does Not Include Discovery-Domain Facts". Tool-detection facts that *would* come from adapters (e.g. `mokutil` not found) are not surfaced to the user via `bcs doctor`.

**Resolved real-world symptoms:** the first real-world validation run (Ubuntu 24.04, VirtualBox, SATA disk — see `docs/REAL_WORLD_VALIDATION.md`) showed `bcs inventory` reporting `storage: []` on a machine where `lsblk` correctly enumerated `/dev/sda` and its partitions. Root cause: `collect_storage()` (`cli/src/bcs/inventory/collectors.py`) intentionally enumerates only `/dev/nvme*` (per `PLAT-005`), while the Storage Adapter enumerates every device `lsblk` reports. `bcs inventory` now translates and reports the Storage Adapter's output when the orchestrator's `storage` slot is available, resolving this specific symptom. Separately, `NetworkInterface.ip_addresses` was a permanent placeholder gap in `bcs inventory` output — `collect_network()` never populated it (pure-stdlib IP discovery wasn't in scope); `bcs inventory` now translates and reports the Network Adapter's `ip -json addr show` data when the orchestrator's `network` slot is available, closing that gap too (Beta M3). Re-validation on the same VM belongs in `docs/VM_TEST_LOG.md` as a new entry, not as an edit to `docs/REAL_WORLD_VALIDATION.md` (a fixed historical record by its own stated policy).

**Tracking:** `docs/HOST_DISCOVERY_ORCHESTRATOR.md` status banner; `docs/IMPLEMENTATION_STATUS.md §8` Outstanding Work; `docs/ISSUE_70_IMPLEMENTATION_CHECKLIST.md`; `docs/BETA_ROADMAP.md` (Milestone M3); issue [#70](https://github.com/nino79/batoi-classroom-suite/issues/70) (`bcs inventory` storage — done) and issue [#78](https://github.com/nino79/batoi-classroom-suite/issues/78) (the full legacy-collector deprecation arc this fits into, including `bcs doctor`).

## 7 Stub Commands

**Severity:** Medium — by design per MVP scope

`build`, `install`, `deploy`, `backup`, `restore`, `update`, `config` are registered in the command tree so `bcs --help` reflects the full planned surface. Each is a stub that prints "not implemented in this phase" and exits non-zero. No Boot Manager, Builder, or Deploy logic exists in this package.

**Impact:** The CLI is not usable for its ultimate purpose yet.

**Tracking:** Phases 1-3 on `ROADMAP.md`.

## Host Inventory Schema Does Not Include Discovery-Domain Facts

**Severity:** Medium — planned enhancement

`firmware_boot_configuration`, `storage_topology`, `secure_boot`, and `filesystem_usage` live on `HostDiscoverySnapshot` but are never folded into `HostInventory`'s own schema. Per ADR-0011 Decision point 6, this requires a separate ADR-0008 amendment.

**Impact:** `bcs inventory --output json` does not include UEFI boot entries, detailed storage topology, or Secure Boot status from the tool-based adapters.

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

## `_read_secure_boot_state()` Collector Returns Placeholder `UNKNOWN`

**Severity:** Medium — inventory Secure Boot field is always `UNKNOWN`

The legacy `bcs.inventory.collectors._read_secure_boot_state()` function (`cli/src/bcs/inventory/collectors.py:86`) always returns `SecureBootState.UNKNOWN`. The comment at line 89–91 explicitly marks it as "a placeholder for future work." The tool-based Secure Boot Adapter (`bcs.platform.adapters.secureboot`) correctly reads `mokutil --sb-state`, but its output is held in `HostDiscoverySnapshot.secure_boot` — which no `bcs` command consumes.

**Impact:** `bcs inventory` always reports `secureBoot: unknown` regardless of actual firmware state. `bcs doctor --check secure-boot` uses the adapter path (via `HostDiscoverySnapshot`) only when the orchestrator is passed through — which currently never happens — so `bcs doctor secure-boot` also returns `UNKNOWN` on the legacy path.

**Tracking:** `docs/HOST_DISCOVERY_ORCHESTRATOR.md` status banner; `docs/IMPLEMENTATION_STATUS.md §8` Outstanding Work (High).

## `FrozenModel`/`FrozenExtensibleModel` Not Relocated

**Severity:** Low — cosmetic

The `FrozenModel`/`FrozenExtensibleModel` base classes (defined in `bcs.config.models` and replicated in `bcs.inventory.models`) have not been consolidated into `bcs.model_utils`.

**Impact:** Two copies of nearly identical Pydantic base classes.

**Tracking:** `docs/PLATFORM_LAYER.md § Approved Design Decisions`, item 5.

## CLI.md References Stale Implementation Status

**Severity:** Informational — design doc not updated

`docs/CLI.md` line 98 still refers to ADR-0009 as "(Accepted, not yet implemented)" — the Platform Layer is fully implemented (Parts 1-4). This is a documentation staleness issue in the design document.

**Note:** This document (`docs/CLI.md`) is a technical design document and is not being updated in this pass per project conventions. See the CLI design document itself for authoritative design; see `docs/IMPLEMENTATION_STATUS.md` for current implementation state.
