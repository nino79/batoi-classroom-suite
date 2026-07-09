# Technical Debt Index — BCS Codebase

**Generated:** 2026-07-09
**Method:** Grep of `cli/src/`, `docs/`, and `scripts/` for patterns: `TODO`, `FIXME`, `XXX`, `HACK`, `placeholder`, `deprecated`, `not implemented`, `pending`, `future work`. Vendor directories excluded. Each item classified as `HIGH`, `MEDIUM`, or `LOW`.

---

## Production Code (`cli/src/bcs/`)

### HIGH

| ID | File | Line | Pattern | Content | Notes |
|---|---|---|---|---|---|
| TD-H01 | `collectors.py` | 89-92 | `placeholder` | `_read_secure_boot_state()` — `# Parsing the SecureBoot-<GUID> EFI variable's actual byte value is a placeholder for future work; presence of efivars only confirms the firmware exposes UEFI variables at all, not the Secure Boot toggle.` | This function always returns `UNKNOWN`. The Secure Boot Adapter now provides real data, but this private helper still runs on every `collect_firmware()` call (see COLLECTOR_USAGE_CENSUS.md). |
| TD-H02 | `collectors.py` | 98-104 | `deprecated` | `collect_storage()` — RST `.. deprecated::` annotation | Category B collector — fallback-only via inventory, primary via doctor. Cannot be removed until doctor migrates. |
| TD-H03 | `collectors.py` | 266-273 | `deprecated` | `collect_network()` — RST `.. deprecated::` annotation | Category B collector — fallback-only via inventory (Beta M3), primary via doctor. Cannot be removed until doctor migrates. |
| TD-H04 | `app.py` | 218 | `(silent)` | `filesystem=functools.partial(read_filesystem_usage, runner=command_runner)` | Filesystem adapter runs `df` subprocess on every CLI invocation but its output is never consumed (no `HostInventory` field exists). Wasted subprocess — see UNUSED_PLATFORM_ADAPTERS.md. |

### MEDIUM

| ID | File | Line | Pattern | Content | Notes |
|---|---|---|---|---|---|
| TD-M01 | `collectors.py` | 17 | `placeholder` | `These collectors are Linux-oriented placeholders (``/sys``, ``/proc``, ``/dev``)` | Module-level docstring uses "placeholders" for all collectors, but 4 are permanent (pure Python) and several are now fallback-only. Misleading characterization. |
| TD-M02 | `collectors.py` | 90 | `placeholder` | `# placeholder for future work; presence of efivars only confirms the firmware exposes UEFI variables at all, not the Secure Boot toggle.` | Comment describes `_read_secure_boot_state()` as a placeholder. The function itself still exists and is still dead logic (always returns UNKNOWN), but the real Secure Boot data now comes from the adapter. Comment could be updated. |
| TD-M03 | `collectors.py` | 261-264 | `placeholder` | `IP address enumeration is a known placeholder gap (empty ``ipAddresses``): pure-stdlib, per-interface IP discovery isn't portable without either a new dependency or shelling out to ``ip``/``ifconfig``, neither of which is in scope for this pass.` | This gap is closed (Beta M3) via the Network Adapter. The `collect_network()` docstring still describes it as a gap. |
| TD-M04 | `platform/__init__.py` | 17 | `placeholder` | `yet; ``mount``/``rsync`` remain undesigned placeholders.` | Accurately describes future adapters — no action needed. |
| TD-M05 | `commands/stubs.py` | 1 | `placeholder` | `"""Placeholder registrations for commands not implemented in this phase.` | Accurately describes stub commands — these will remain stubs until Phases 1-3. No action needed. |
| TD-M06 | `commands/stubs.py` | 48, 54 | `not implemented` | `"""Report that ``stub`` is not implemented in this phase, and stop."""` + `f"bcs {stub.name}: not implemented in this phase. "` | Accurately describes stub behavior — no action needed. |
| TD-M07 | `app.py` | 303 | `not implemented` | `help=f"(not implemented in this phase) owned by {_stub_command.owner}.",` | Stub help text — accurate. No action needed. |
| TD-M08 | `commands/doctor.py` | 211 | `placeholder` | `"PXE/multicast reachability itself remains a placeholder (PLAT-007)"` | Network check message accurately describes a known limitation. No action needed. |
| TD-M09 | `commands/doctor.py` | 144 | `placeholder` | `placeholder, so a ``PlatformError`` (e.g. ``lsblk`` missing) falls` | Docstring describes `collect_storage()` as producing "real, useful (if NVMe-only) data rather than a permanent placeholder" — accurate. No action needed. |

### LOW

| ID | File | Line | Pattern | Content | Notes |
|---|---|---|---|---|---|
| TD-L01 | `config/loader.py` | 83 | `not yet` | `"""Load, override, but do not yet schema-validate, a config file."""` | Accurately describes that `load()` does not validate — validation happens elsewhere. No action needed. |
| TD-L02 | `platform/adapters/filesystem/parser.py` | 110 | `placeholder` | ``# `df`'s own "not supported for this filesystem type" placeholder for`` | Comment about `df`'s `-` token — accurate. No action needed. |

---

## Documentation (`docs/`)

### HIGH

| ID | File | Line | Pattern | Content | Notes |
|---|---|---|---|---|---|
| TD-D01 | `BETA_PREPARATION_REPORT.md` | Multiple | `(stale)` | Report describes state before Beta M3/M4/M5/M6 — 4 claims that contradict current reality (Network Adapter unwired, empty storage array, HDO unconsumed, SB placeholder) | **FIXED** — documented in BETA_READINESS_AUDIT.md §2.5. Reader should consult IMPLEMENTATION_STATUS.md instead. |
| TD-D02 | `SECURE_BOOT_DOCUMENTATION_AUDIT.md` | Multiple | `(stale)` | Outdated audit pre-dating Beta M4; lists placeholder gaps already closed | **ARCHIVE** — superseded by accepted SECURE_BOOT_ADAPTER.md. |
| TD-D03 | `MVP_DEMO_PLAN.md` | 94-96 | `not yet` | `"Network adapter implemented but not yet wired in"` + `"No CLI command passes the orchestrator through yet"` | **FIXED** — both now true (Beta M3). Updated in this session. |

### MEDIUM

| ID | File | Line | Pattern | Content | Notes |
|---|---|---|---|---|---|
| TD-D04 | `BETA_VALIDATION_PLAN.md` | 25 | `not yet wired` | `"The Host Discovery Orchestrator consumption path (not yet wired into any command)"` | **FIXED** — updated in this session. |
| TD-D05 | `LEGACY_COLLECTOR_DEPRECATION_PLAN.md` | 15 | `(broken link)` | Reference to `COLLECTOR_CENSUS.md` (non-existent) | **FIXED** — updated to point to `COLLECTOR_USAGE_CENSUS.md` in this session. |
| TD-D06 | `ISSUE_70_IMPLEMENTATION_CHECKLIST.md` | Multiple | `(superseded)` | Checklist for issue #70 which is now closed | Keep as historical record — linked from GitHub issue. |
| TD-D07 | `SECURE_BOOT_IMPLEMENTATION_PLAN.md` | Header | `not implemented` | `"Status: Analysis and planning only — nothing in this document has been implemented."` | This doc was the pre-implementation plan for Beta M4, which is now code-complete. Stale header. |
| TD-D08 | `HDO_MIGRATION_PLAN.md` | 120 | `(superseded)` | `"collect_host_inventory() no longer calls legacy collectors at all"` — describes a future state not yet reached | Working plan doc — accurately describes aspirational state. Keep. |

### LOW

| ID | File | Line | Pattern | Content | Notes |
|---|---|---|---|---|---|
| TD-D09 | `PLATFORM_LAYER.md` | 262 | `placeholder` | `no real output has been captured yet (placeholders only)` | Fixture corpus statement — still accurate. No action needed. |
| TD-D10 | `PLATFORM_LAYER.md` | 302 | `placeholder` | Describes collector placeholder gaps as "resolved" — accurate. | No action needed. |
| TD-D11 | `HOST_INVENTORY.md` | 406 | `placeholder` | `a placeholder recorded in the legacy collector's own docstring` — accurately describes historical state. | No action needed. |
| TD-D12 | `NETWORK_ADAPTER.md` | 11 | `placeholder` | `Host Inventory's network collection is a sysfs-only placeholder` — accurate historical context. | No action needed. |
| TD-D13 | `SECURE_BOOT_ADAPTER.md` | 11 | `placeholder` | `Host Inventory's own documented gap — resolved, Beta M4` — accurately resolves placeholder. | No action needed. |
| TD-D14 | `KNOWN_LIMITATIONS.md` | 13 | `placeholder` | Describes resolved placeholder gaps as "resolved" — accurate. | No action needed. |

---

## Scripts (`scripts/`)

No `TODO`/`FIXME`/`XXX` markers found in any Bash script under `scripts/`. Zero technical debt detected in script files.

---

## Summary

| Severity | Count | Key Items |
|---|---|---|
| **HIGH (code)** | 4 | Dead `_read_secure_boot_state()` always-UNKNOWN; deprecated collectors awaiting doctor migration; wasted filesystem adapter subprocess |
| **MEDIUM (code)** | 4 | Stale docstring claiming IP gap still open; module docstring mischaracterizes permanent collectors as "placeholders" |
| **HIGH (docs)** | 3 | Stale preparation report (known); stale audit (should archive); stale demo plan (fixed) |
| **MEDIUM (docs)** | 5 | 2 stale references fixed in this session; broken link fixed; 2 working plans |
| **LOW (both)** | 15 | Accurate historical references; no action needed |
