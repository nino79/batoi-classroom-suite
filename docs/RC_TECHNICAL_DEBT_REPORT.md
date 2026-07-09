# RC Technical Debt Report — `bcs` CLI

**Date:** 2026-07-09
**Scope:** Complete repository analysis of `cli/` for dead code, unused imports/helpers, duplication, obsolete compatibility code, legacy fallbacks, unreachable branches, unused adapters/models, obsolete comments, temporary workarounds, placeholder implementations, deprecated APIs, and stale documentation references.
**Method:** Built on top of the existing `docs/COLLECTOR_USAGE_CENSUS.md`, `docs/COLLECTOR_CALL_GRAPH.md`, `docs/UNUSED_PLATFORM_ADAPTERS.md`, and `docs/TECHNICAL_DEBT_INDEX.md` (all generated earlier the same day by a concurrent session) — re-verified against the current source rather than re-derived from scratch, with two of their claims corrected below (see [Corrections](#corrections-to-existing-analysis)). Nothing in this report was removed; per this pass's own instructions, this is classification only.
**No production code was changed to produce this report.**

---

## Classification Legend

| Class | Meaning |
|---|---|
| **KEEP** | Working as intended, or intentionally provisional in a way that doesn't cost anything to leave in place. No action before or after Beta. |
| **REMOVE AFTER BETA** | Safe to remove once its blocking condition (a doctor migration, an ADR amendment, a hardware validation result) is met — not before, since removing it now would delete behavior Beta still needs. |
| **REMOVE BEFORE RC** | Should be removed (or fixed) before tagging a Release Candidate — either genuinely dead code, or a doc/comment inaccuracy cheap enough to fix now and confusing enough to leave. |
| **DISCUSS** | Removal isn't obviously safe or obviously unsafe; a maintainer decision is needed (usually because removing it forecloses an option, like a future adapter, that nothing has decided to abandon yet). |

---

## Findings

### Dead / unreachable code

| # | Item | Location | Class | Rationale |
|---|---|---|---|---|
| 1 | `_read_secure_boot_state()` — always returns `SecureBootState.UNKNOWN` | `cli/src/bcs/inventory/collectors.py:86-92` | **DISCUSS** | Genuinely dead in the sense that it can never return anything but `UNKNOWN` — the byte-parsing it would need was never implemented, and the Secure Boot Adapter (M4) now supplies the real value via `service.py`'s override path. But it is still the *only* source `collect_firmware()` has for `secure_boot` when no orchestrator is passed (`collect_host_inventory()` called with `orchestrator=None`) or when the Secure Boot Adapter's slot raised a `PlatformError`. Removing the function would leave that fallback path with no value to return at all — not a cleanup, a behavior change. Belongs in the Legacy Exit Plan's dependency chain, not a standalone deletion. |
| 2 | `cpu`/`memory` fallback branches in `collect_host_inventory()`'s orchestrator path | `cli/src/bcs/inventory/service.py:184-185` | **DISCUSS**, not REMOVE — see [Corrections](#corrections-to-existing-analysis) | Verified: `collectors.collect_cpu`/`collect_memory` are bound directly as the HDO `cpu`/`memory` adapter slots (`app.py:220-221`), and both functions are defensive-by-design (per their own docstrings, `bcs.inventory.collectors`' module doc: "never an exception"). `_call_adapter()` in `orchestrator.py` only returns `None` for an unset slot or a caught `PlatformError` — since these two adapters are always wired and never raise, `snapshot.cpu`/`snapshot.memory` cannot be `None` in production today, so lines 184-185's `else` branches are unreachable right now. **But**: `KNOWN_LIMITATIONS.md`'s "No CPU/Memory/TPM Tool-Based Adapters" entry explicitly anticipates these being replaced by real tool-based adapters later (e.g. a `dmidecode`-based one) — and a real adapter *can* raise `PlatformError`. Deleting the fallback now would reintroduce exactly the crash-on-missing-tool risk the fallback exists to prevent, the moment that future adapter lands. Keep until that future adapter is either built or explicitly declined. |
| 3 | `storage`/`network` fallback branches in `collect_host_inventory()`'s orchestrator path | `cli/src/bcs/inventory/service.py:186-195` | **KEEP** | Unlike #2, these *are* reachable in production: the Storage/Network Adapters shell out (`lsblk`/`blkid`/`findmnt`, `ip -json addr show`) and can genuinely raise `PlatformError` (tool missing, non-zero exit, malformed output) even on an otherwise healthy machine. `COLLECTOR_CALL_GRAPH.md` classifies these identically to the cpu/memory ones ("unreachable on healthy systems") — that claim does not hold for storage/network; see [Corrections](#corrections-to-existing-analysis). |

### Legacy fallbacks (collectors superseded by adapters)

Full detail in `docs/RC_LEGACY_EXIT_PLAN.md` (Phase 2 of this pass). Summary classification here:

| # | Item | Class | Rationale |
|---|---|---|---|
| 4 | `collect_storage()` — `.. deprecated::` annotation, `collectors.py:95-111` | **REMOVE AFTER BETA** | Still the primary source for `bcs doctor --check storage`'s fallback and the no-orchestrator path in `collect_host_inventory()`. Cannot be removed until `bcs doctor` is confirmed stable on real hardware post-M5, and even then only the *primary-use* callers migrate — the fallback role likely stays (see #3). |
| 5 | `collect_network()` — `.. deprecated::` annotation, `collectors.py:258-289` | **REMOVE AFTER BETA** | Same shape as #4, network domain. |
| 6 | `collect_efi_system_partition()` | **DISCUSS** | Not deprecated-annotated at all (no adapter exists that already does this job) — it is not legacy in the "superseded" sense, only in the sense that its logic *could* one day move into a business-logic service built on the Storage Adapter's `BlockDevice.partitions`. That service doesn't exist and isn't scoped for Beta. Nothing to remove; flagged here only because `COLLECTOR_USAGE_CENSUS.md` groups it with the others. |
| 7 | `collect_usb_storage()` | **DISCUSS** | Same reasoning as #6, `BlockDevice.is_removable` instead of `.partitions`. |
| 8 | `collect_identity()` | **KEEP** | No adapter equivalent is even planned (speculative only); this is a permanent collector, not technical debt. |

### Unused / partially-used adapters

| # | Item | Class | Rationale |
|---|---|---|---|
| 9 | EFI Adapter (`read_firmware_boot_configuration`) — wired, invoked by the orchestrator every run, output discarded | **DISCUSS** | Per `docs/UNUSED_PLATFORM_ADAPTERS.md`: `efibootmgr` runs on every `bcs inventory`/`bcs doctor` invocation and its parsed `FirmwareBootConfiguration` is never read by anything. This is architecturally accepted-but-deferred (ADR-0011 Decision point 6 explicitly defers folding Discovery-domain facts into `HostInventory`'s schema to a separate ADR-0008 amendment) — not drift, not a bug, but real wasted subprocess work on every invocation until that amendment lands or the slot is unwired. A maintainer call, not a cleanup. |
| 10 | Filesystem Adapter (`read_filesystem_usage`) — wired, invoked every run, output discarded | **DISCUSS** | Same shape as #9, `df` subprocess. `docs/UNUSED_PLATFORM_ADAPTERS.md`'s own recommendation (unwiring the `filesystem` slot in `app.py` until a consumer exists, a one-line change) is a reasonable option, but unwiring a Discovery slot is exactly the kind of "no architectural drift" question Phase 3 of this pass is scoped to *flag*, not decide — see `docs/RC_LEGACY_EXIT_PLAN.md`. |
| 11 | Secure Boot Adapter's `setup_mode`/`raw_text` fields — produced, never read | **KEEP** | `state` (the field that matters for Beta) is fully consumed. The other two fields are informative/debug-only per `docs/UNUSED_PLATFORM_ADAPTERS.md`; no cost to leaving them unconsumed, no removal candidate (they're part of the adapter's already-accepted model, not applied dead code). |
| 12 | `HostDiscoverySnapshot.caveats` — collected by the orchestrator, never read by any command | **DISCUSS** | Real information (which adapter failed and why) is silently discarded today. Not a defect — no CLI command currently has a designed place to show it — but worth a maintainer decision before RC: either design a minimal surfacing (e.g. a `caveats` line in `bcs doctor`/`bcs inventory` text output) or explicitly declare it out of scope for this Beta cycle so it stops looking like an oversight. |

### Obsolete comments / stale docstrings

| # | Item | Class | Rationale |
|---|---|---|---|
| 13 | `collectors.py:17-20` module docstring calls all ten collectors "placeholders" | **REMOVE BEFORE RC** | Four collectors (`cpu`, `memory`, `operating_system`, `tooling`) are permanent, pure-Python, never-deprecated code — calling them "placeholders" in the module's own docstring actively misleads a reader auditing this file for what's provisional vs. permanent, exactly the kind of confusion this RC pass exists to remove. Cheap, low-risk documentation fix. |
| 14 | `collect_network()` docstring: "IP address enumeration is a known placeholder gap (empty `ipAddresses`)" | **REMOVE BEFORE RC** | This gap closed in Beta M3 (Network Adapter). The docstring describes a problem that no longer exists for the primary (adapter) path — it's still true for this *specific fallback function*, but the framing ("known placeholder gap") reads as if the whole feature is still missing. Should be reworded to say this collector's own IP enumeration is intentionally absent because the Network Adapter is the real source now. |
| 15 | `_read_secure_boot_state()` comment: "placeholder for future work" | **KEEP**, reword optional | Technically still accurate (the function itself is unchanged and still a placeholder) — but see finding #1: since Beta M4, this placeholder is now only the last-resort fallback, not "future work" in the sense of something actively planned. Low priority; doesn't block RC. |
| 16 | ADR-0011's own "Consequences" section: *"Not yet implemented: no CLI command passes `runtime.host_discovery_orchestrator` into `collect_host_inventory()` yet"* | **REMOVE BEFORE RC** | This is now false — `bcs inventory` has passed the orchestrator through since the issue #70/Beta M3 work. An **accepted ADR's own text** describing current implementation state incorrectly is a real staleness bug (AGENTS.md: "a document that still contradicts an Accepted ADR is a staleness bug to flag or fix, not a sign the ADR is optional" — here the ADR's *own prose* is what's stale, not a downstream doc). See [Phase 3](#phase-3-architecture-verification-summary) below. |

### Deprecated APIs

| # | Item | Class | Rationale |
|---|---|---|---|
| 17 | `collect_storage()`/`collect_network()` RST `.. deprecated::` annotations | **KEEP** (annotation itself), tracked under #4/#5 | The annotations are accurate and exactly the right way to flag "fallback-only, scheduled for removal once doctor migrates" — this is good practice, not debt. Debt is in the underlying migration not being done yet, already captured above. |

### Duplication

| # | Item | Class | Rationale |
|---|---|---|---|
| 18 | `if runtime.output is OutputFormat.TEXT: ... else: print_structured_result(...)` repeated in `doctor.py`, `inventory.py`, `validate.py`, `version.py` | **KEEP** | Genuine but proportionate duplication — each command's TEXT branch renders meaningfully different content, and the shared JSON/YAML path is already factored into `bcs.output.print_structured_result`. Abstracting the 2-line dispatch itself would be premature generalization for no real gain (three/four similar lines, not a growing pattern). |
| 19 | Per-adapter package shape (`models.py`/`parser.py`/`errors.py`/`adapter.py`) repeated 5× (EFI, Storage, Secure Boot, Filesystem, Network) | **KEEP** | This is the intended, documented pattern (`docs/PATTERNS.md`), not duplication — each adapter's domain logic differs; only the *shape* repeats, which is exactly what a consistent pattern should do. |

### Placeholder implementations

| # | Item | Class | Rationale |
|---|---|---|---|
| 20 | 7 stub commands (`build`, `install`, `deploy`, `backup`, `restore`, `update`, `config`) | **KEEP** | By design — Phases 1-3 haven't started (AGENTS.md Hard Constraint 1). Not technical debt; this is the correct MVP shape. |
| 21 | `bcs.commands.doctor`'s `esp`/`usb-storage` checks — collector-only, no adapter equivalent | **REMOVE AFTER BETA** (i.e. once the interpretive business-logic service from findings #6/#7 exists) | Tracked identically in `KNOWN_LIMITATIONS.md`; no new information here beyond confirming it's still accurate post-M4. |

---

## Corrections to Existing Analysis

Two claims in the concurrent session's same-day analysis docs were checked against the current source and found inaccurate; corrected here rather than in those docs (not this pass's file to edit):

1. **`docs/COLLECTOR_CALL_GRAPH.md` overstates which orchestrator-path fallbacks are dead.** It classifies all four of `service.py`'s orchestrator-path fallback branches (`cpu:184`, `memory:185`, `storage:189`, `network:194`) as *"Should disappear — unreachable on healthy systems (HDO slot always populated)."* Verified directly against `orchestrator.py`'s `_call_adapter()`: a slot is `None` only when unset or its adapter raised `PlatformError`. `collect_cpu`/`collect_memory` are pure-Python and defensive-by-contract (never raise) — so yes, unreachable today (finding #2 above). But the Storage/Network Adapters *do* shell out and *can* raise `PlatformError` on a real machine missing `lsblk`/`ip` or hitting a parse failure — their fallback branches are reachable in production, not just in tests (finding #3 above). The blanket claim should be split in two.
2. **`KNOWN_LIMITATIONS.md`'s "`FrozenModel`/`FrozenExtensibleModel` Not Relocated" entry mischaracterizes `bcs.config.models`.** (Noted previously in `docs/BETA_READINESS_REPORT.md` §Known Limitations; repeated here since it's in scope for this pass too.) `bcs.config.models` does not define classes named `FrozenModel`/`FrozenExtensibleModel` — it has `StrictModel`/`ExtensibleModel`, and per ADR-0008, only `bcs.inventory.models` is required to be frozen (`ConfigDict(frozen=True, ...)`); ClassroomConfig documents are a different subsystem with different mutability needs. This is not architectural drift — ADR-0008 never mandated freezing config models — just an imprecise limitation-doc description. **REMOVE BEFORE RC** (the doc wording, not code).

---

## Phase 3: Architecture Verification Summary

Full detail below in this same document's [Architecture Verification](#architecture-verification) section (Phase 3 of this pass, kept in this file rather than a fifth new document since the user's Phase 4 checklist references its outcome directly).

---

## Architecture Verification

Verified against ADR-0008, ADR-0009, ADR-0011, and the Platform Layer / Host Discovery / RuntimeContext / Composition Root / DI / Adapters-Ports structures they govern. **No architectural drift found in the code itself.** Two documentation-only staleness issues were found in the ADRs' own text (not in the architecture they describe):

| # | ADR | Check | Result |
|---|---|---|---|
| A1 | ADR-0008 (Host Inventory ports-and-adapters, immutability, JSON canonical) | `bcs.inventory.models` — all frozen? | ✅ Compliant. `FrozenModel`/`FrozenExtensibleModel` both set `ConfigDict(frozen=True, ...)` (`inventory/models.py:46-59`). `bcs.commands.inventory`/`bcs.commands.doctor` are the only adapters over the core; no framework imports leaked into `bcs.inventory.models`/`.collectors`/`.service`. |
| A2 | ADR-0008 amendment (ESP/USB Storage) | `EfiSystemPartition`/`UsbStorageDevice` implemented as documented? | ✅ Compliant — both exist, both wired into `collect_host_inventory()` and `bcs doctor`'s `esp`/`usb-storage` checks, exactly as the amendment's Consequences describe. |
| A3 | ADR-0009 (Platform Layer sole path to process execution) | Only `bcs.plugins` and `bcs.platform.execution` import `subprocess`? | ✅ Compliant — verified by direct grep across `cli/src/`: exactly those two files, zero others. |
| A4 | ADR-0009 point 8 | `cli/pyproject.toml`'s `S603`/`S607` Ruff ignores narrowed to those same two files? | ❌ **Not compliant.** `[tool.ruff.lint] ignore = ["S603", "S607"]` is still a blanket, repository-wide ignore — never narrowed to per-file scope. The ADR's own Consequences section states *"any new direct `subprocess` usage outside the two named exceptions fails CI lint automatically, once implemented"* — it is not yet implemented, so that guardrail does not currently exist. Already tracked as a Low-severity item in `KNOWN_LIMITATIONS.md`; this verification ties it explicitly to ADR-0009 non-compliance rather than a generic to-do. No actual violation exists today (A3), but nothing would catch one tomorrow. |
| A5 | ADR-0009 (`RuntimeContext.command_runner` DI, no module-level singleton) | `SubprocessCommandRunner` constructed once, injected via `RuntimeContext`? | ✅ Compliant — `app.py`'s `main()` builds it once per invocation (`command_runner = SubprocessCommandRunner()`), threads it through `RuntimeContext` and into every adapter binding. No global/singleton anywhere. |
| A6 | ADR-0011 (Host Discovery Orchestrator: 8 named slots, no interpretation, per-domain isolation) | `HostDiscoveryOrchestrator.discover()` matches the design? | ✅ Compliant — `orchestrator.py`'s `_call_adapter()` isolates `PlatformError` per domain into `caveats`, never merges/ranks/interprets, calls adapters in the documented fixed order, never imports `subprocess`/`CommandRunner`. |
| A7 | ADR-0011 (composition root binds adapters once, RuntimeContext carries the orchestrator) | `app.py` wiring matches? | ✅ Compliant — all 5 tool-based adapters + `cpu`/`memory` bound once in `main()`, `tpm` correctly left unset (no adapter exists), orchestrator built once and stored on `RuntimeContext.host_discovery_orchestrator`. |
| A8 | ADR-0011 ("`bcs doctor` reads one named slot off `HostDiscoveryAdapters` directly," never `orchestrator.discover()`) | Literal implementation shape matches the ADR's own description? | ⚠️ **Prose mismatch, not a violation.** `doctor.py`'s `_check_storage`/`_check_network`/`_check_secure_boot` import `read_storage_topology`/`read_network_interfaces`/`read_secure_boot_status` directly from their adapter modules and call them with `runtime.command_runner` — they do **not** obtain an already-bound callable from `HostDiscoveryAdapters` (which has no public accessor for individual slots; `HostDiscoveryOrchestrator._adapters` is private). The ADR's decision — never `orchestrator.discover()` in doctor, per-check independence, `PlatformError` isolation per check — is fully honored; only the ADR's own descriptive phrase ("reads one named slot off `HostDiscoveryAdapters`") doesn't precisely describe how that's achieved, since no such read path is structurally exposed. Cosmetic — worth a one-sentence ADR clarification, not a code change. |
| A9 | ADR-0011 Consequences (current implementation status as recorded in the ADR text) | Accurate as of today? | ❌ **Stale.** Says *"no CLI command passes `runtime.host_discovery_orchestrator` into `collect_host_inventory()` yet"* — false since the issue #70/Beta M3 work landed. Same finding as #16 above. |

**Conclusion: no drift in the architecture itself.** Every hard rule (Platform Layer is the sole subprocess path, Host Inventory core stays presentation-agnostic and immutable, the Orchestrator never interprets/merges, `doctor` never calls `orchestrator.discover()`, DI via `RuntimeContext` with no singletons) is followed in the code exactly as decided. The two real issues found (A4, A9) are the ADRs' own prose falling behind the implementation they govern — worth a documentation-only fix, not a design conversation, and not blocking for RC on their own.

---

## Summary

| Class | Count |
|---|---|
| KEEP | 10 |
| REMOVE AFTER BETA | 4 |
| REMOVE BEFORE RC | 4 |
| DISCUSS | 7 |

No item in this report is, by itself, a Release Candidate blocker. The **REMOVE BEFORE RC** items (findings #13, #14, #16, and the `KNOWN_LIMITATIONS.md` wording correction) are all documentation/comment fixes with zero behavioral risk and should be batched into one small documentation pass before tagging RC. Everything else either needs to wait for a specific unblocking event (Beta hardware validation, an ADR-0008 amendment, a doctor migration — tracked in `docs/RC_LEGACY_EXIT_PLAN.md`) or needs an explicit maintainer decision that this pass is not authorized to make unilaterally (the **DISCUSS** items).
