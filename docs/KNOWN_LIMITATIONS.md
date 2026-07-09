# Known Limitations — `bcs` CLI, Phase 0

This document records limitations and gaps in the current implementation. These are **known, accepted, and tracked** — not bugs to be surprised by. Each item links to its owning design document, ADR, or issue for detail.

## Host Discovery Orchestrator Not Consumed by Any Command

**Severity:** High — blocks the "single source of truth" goal

The `HostDiscoveryOrchestrator` is fully implemented, wired into `RuntimeContext` at the composition root, and test-verified end to end. However, no `bcs` command passes `runtime.host_discovery_orchestrator` into `collect_host_inventory()` — `bcs inventory` and `bcs doctor` still source every fact from the original ten `bcs.inventory.collectors` directly.

**Impact:** Adapter-sourced facts (`firmware_boot_configuration`, `storage_topology`, `secure_boot`) are collected but never reach any command output. Tool-detection facts that *would* come from adapters (e.g. `mokutil` not found) are not surfaced to the user.

**Tracking:** `docs/HOST_DISCOVERY_ORCHESTRATOR.md` status banner; `docs/IMPLEMENTATION_STATUS.md §8` Outstanding Work (High).

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

## Network Adapter Implemented but Not Wired

**Severity:** Medium — completion item

The Network Adapter package (`bcs.platform.adapters.network`) is fully implemented — `models.py`, `errors.py`, `parser.py`, `adapter.py` all exist with 100% test coverage. It is NOT yet wired into the Host Discovery composition root; `bcs.inventory.collectors.collect_network()` (the older `sysfs`-based collector) remains the `network` slot's actual binding.

**Impact:** Network facts come from `sysfs` (no `ip` tool parsing), and `NetworkInterface.ip_addresses` remains a permanent placeholder gap.

**Tracking:** `docs/NETWORK_ADAPTER_IMPLEMENTATION_PLAN.md`.

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

## `FrozenModel`/`FrozenExtensibleModel` Not Relocated

**Severity:** Low — cosmetic

The `FrozenModel`/`FrozenExtensibleModel` base classes (defined in `bcs.config.models` and replicated in `bcs.inventory.models`) have not been consolidated into `bcs.model_utils`.

**Impact:** Two copies of nearly identical Pydantic base classes.

**Tracking:** `docs/PLATFORM_LAYER.md § Approved Design Decisions`, item 5.

## CLI.md References Stale Implementation Status

**Severity:** Informational — design doc not updated

`docs/CLI.md` line 98 still refers to ADR-0009 as "(Accepted, not yet implemented)" — the Platform Layer is fully implemented (Parts 1-4). This is a documentation staleness issue in the design document.

**Note:** This document (`docs/CLI.md`) is a technical design document and is not being updated in this pass per project conventions. See the CLI design document itself for authoritative design; see `docs/IMPLEMENTATION_STATUS.md` for current implementation state.
