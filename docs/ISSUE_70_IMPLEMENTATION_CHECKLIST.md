# Issue #70 Implementation Checklist — Integrate Host Discovery Orchestrator into Inventory Pipeline

This is the working checklist for implementing [issue #70](https://github.com/nino79/batoi-classroom-suite/issues/70). It is a planning artifact, not a design document: the architecture is already decided (see [§ 2. ADR Review](#2-adr-review)); this document exists so implementation can begin immediately, in small, independently-reviewable steps, without re-deriving any of the analysis below.

Scope is exactly issue #70's scope: `HostInventory.storage` sourced from the Host Discovery Orchestrator's Storage Adapter output, with a fallback to the legacy `collect_storage()` collector. Nothing else. See the issue's own **Out of scope** section — repeated nowhere in this document, since duplicating it would risk the two drifting apart.

## 1. Issue Accuracy Verification

Every code citation in issue #70 was checked against the current source tree before writing this checklist. All confirmed accurate — no factual drift since the issue was filed:

| Claim | File:Line | Verified |
|---|---|---|
| `run_inventory()` calls `collect_host_inventory()` with zero arguments | `cli/src/bcs/commands/inventory.py:135` | ✅ Exact match |
| `collect_storage()` globs only `/dev/nvme[0-9]n[0-9]` | `cli/src/bcs/inventory/collectors.py:95-102` | ✅ Exact match |
| Orchestrator branch covers only `cpu`/`memory`/`network`; `storage` unconditional | `cli/src/bcs/inventory/service.py:72-102` (branch at 80-88, `storage=` at 98) | ✅ Exact match |
| `_check_storage()` calls `collect_storage()` directly | `cli/src/bcs/commands/doctor.py:73-78` | ✅ Exact match |
| `is_nvme=name.startswith("nvme")` is descriptive, not a filter | `cli/src/bcs/platform/adapters/storage/parser.py:199` | ✅ Exact match |
| `StorageDevice` fields: `name`, `path`, `is_nvme`, `size_bytes`, `model` | `cli/src/bcs/inventory/models.py:102-109` | ✅ Exact match |
| `HostDiscoverySnapshot.storage_topology: StorageConfiguration \| None`, `.cpu`/`.memory` typed as `bcs.inventory.models.CpuInfo`/`MemoryInfo` directly | `cli/src/bcs/inventory/discovery/models.py` | ✅ Exact match |

Two clarifications were made to the issue itself (not a scope change — see the issue's own accuracy-pass comment):

1. Added an explicit **Out of scope** entry: `bcs doctor`'s `storage`/`esp` checks call collectors directly, independent of `collect_host_inventory()`, by deliberate design (`docs/HOST_INVENTORY.md` § "Why `commands.doctor` depends on `inventory.collectors` directly, not `inventory.service`" — documented specifically to prevent this exact "fix," since a shared dependency path would remove `doctor`'s check-isolation guarantee). This issue does not touch `commands/doctor.py`.
2. Testing Strategy: flagged two concrete, verified test breakages (not just "extensions") — see [§ 4](#4-test-suite-review).

## 2. ADR Review

Reviewed: [ADR-0008](decisions/0008-host-inventory-ports-and-adapters.md) (Host Inventory), [ADR-0009](decisions/0009-platform-layer-command-runner.md) (Platform Layer), [ADR-0010](decisions/0010-efi-adapter-read-only-scope.md) (EFI Adapter — checked for any generic wiring rule; found none beyond what 0009 already states), [ADR-0011](decisions/0011-host-discovery-orchestrator.md) (Host Discovery Orchestrator), and ADR-0006/0007 (CLI architecture / Python choice — checked for `RuntimeContext`-specific decisions; found none, `RuntimeContext.host_discovery_orchestrator` is governed entirely by ADR-0011).

**Conclusion: no ADR change required — no amendment, no new ADR.**

This is not a judgment call; it is a literal reading of decisions already on record:

- **ADR-0011 Decision point 7 and its own Consequences section already describe and accept exactly this pattern**, for `cpu`/`memory`/`network`: *"`bcs.inventory.service.collect_host_inventory()` gains an `orchestrator` parameter... sourcing `cpu`/`memory`/`network` from the resulting `HostDiscoverySnapshot` (with a per-field fallback to the existing collector when a snapshot value is `None`) while every other `HostInventory` field remains collector-sourced exactly as before"* (Consequences, "Implemented (Parts 1–4)" bullet). The italicized clause describes the state *at the time ADR-0011 was accepted*, not a permanent limit — nothing in the ADR forbids extending the same, already-approved mechanism to another field. Issue #70 is that extension, applied to exactly one more field.
- **ADR-0011 Decision point 6** ("does not itself add new fields to `HostInventory`") is satisfied: `HostInventory.storage: list[StorageDevice]` is not a new field, and its type does not change. Only the function that populates it changes.
- **ADR-0008** (`HostInventory`'s own ports-and-adapters/immutability/JSON-canonical decisions) is unaffected: no new field, no schema version bump, `StorageDevice` unchanged, immutability unchanged.
- **ADR-0009** (Platform Layer / `CommandRunner`) is unaffected: this issue does not touch `CommandRunner`, `subprocess`, or any adapter's own execution logic; it only consumes an already-produced `HostDiscoverySnapshot`.
- **The Storage Adapter's own design document already anticipated this split of responsibility**: `docs/STORAGE_ADAPTER.md:237` — *"The translation from `StorageConfiguration` → `HostInventory`... is the responsibility of the inventory collector, not the adapter."* This is independent, pre-existing confirmation that the translation function belongs in `bcs.inventory` (this issue's plan), not in `bcs.platform.adapters.storage`.

If a future issue ever wants to add *new* `HostInventory` fields for the richer facts `StorageConfiguration`/`BlockDevice` carry (partitions, mounts, vendor, serial) that `StorageDevice` has no field for today, *that* would need the ADR-0008 amendment ADR-0011 Decision point 6 already anticipates (tracked in #71). Issue #70 does not do this and does not need it.

## 3. Atomic Implementation Checklist

Each item is independently reviewable — a reviewer should be able to approve or request changes on one box without needing the others done first, though the order below is the dependency order (earlier boxes unblock later ones).

### 3.1 Core translation logic

- [ ] **3.1.1** — Add a private function to `cli/src/bcs/inventory/service.py` translating `StorageConfiguration` → `list[StorageDevice]` (name suggestion: `_translate_storage_devices`, mirroring the module's existing private-helper convention — there are none yet in this file, so this also establishes the pattern). Maps only top-level `BlockDevice` entries in `.devices` (never `.partitions`/`.mounts` — `StorageDevice` has no field for either). Field mapping: `name`→`name`, `path`→`path`, `is_nvme`→`is_nvme`, `size_bytes`→`size_bytes`, `model`→`model`. **Open design question, not resolved by this checklist:** should every `BlockDevice.device_type` be translated (including `loop`, `rom`, `raid`), or only `device_type == "disk"`? The legacy `collect_storage()` implicitly only ever returned physical NVMe disks (its glob cannot match a loop/rom device name); a raw, type-unfiltered translation could introduce spurious entries (e.g. a mounted ISO's loop device) that never appeared in `bcs inventory storage` before. **Recommendation: filter to `device_type == "disk"`,** matching the legacy collector's implicit scope and the "no silent behavior widening beyond what's asked" principle — but this is an implementation decision to make and document at coding time, not to pre-decide here.
- [ ] **3.1.2** — Import `StorageConfiguration`/`BlockDevice` from `bcs.platform.adapters.storage.models` into `service.py`. Verify this doesn't violate layering: `bcs.inventory` depending on `bcs.platform` is the accepted direction (`bcs.inventory.discovery.models` already does this for the same `StorageConfiguration` type — precedent, not a new pattern).

### 3.2 Service-layer wiring

- [ ] **3.2.1** — In `collect_host_inventory()`, move `storage` out of the unconditional `HostInventory(...)` call and into the existing `if orchestrator is None: ... else: ...` block, mirroring `cpu`/`memory`'s exact shape: `else` branch computes `storage = _translate_storage_devices(snapshot.storage_topology) if snapshot.storage_topology is not None else collectors.collect_storage()`.
- [ ] **3.2.2** — `if orchestrator is None` branch gains `storage = collectors.collect_storage()` (currently implicit via the unconditional call — must become explicit once `storage` is a branch-local variable, exactly like `cpu`/`memory`/`network` already are).
- [ ] **3.2.3** — Update the `return HostInventory(...)` call to use the local `storage` variable instead of calling `collectors.collect_storage()` inline.
- [ ] **3.2.4** — Update this module's own docstring (lines ~17-37): the "Omitted (the default)" and "Given" bullets, and the "Every other section... is unaffected either way" sentence, all currently list `storage` among the fields untouched by the orchestrator. This is no longer true and must be corrected in the same change that changes the behavior — this file's docstring is normative documentation for anyone reading the function, not just prose.

### 3.3 CLI wiring

- [ ] **3.3.1** — In `cli/src/bcs/commands/inventory.py`, change `run_inventory()`'s call from `collect_host_inventory()` to `collect_host_inventory(orchestrator=runtime.host_discovery_orchestrator)`.

### 3.4 Test suite changes

See [§ 4](#4-test-suite-review) for the full inventory of which existing tests protect this code, which break, and which are new. Checklist form:

- [ ] **3.4.1** — Fix `test_commands_inventory.py`'s `patched_inventory` fixture (`lambda: fake` → accepts the `orchestrator` kwarg) — **required for the existing suite to pass at all**, not optional.
- [ ] **3.4.2** — Trim `test_orchestrator_other_sections_unaffected` (`test_inventory_service.py`): remove `storage` from its docstring's field list and remove the `assert without_orchestrator.storage == with_orchestrator.storage` line.
- [ ] **3.4.3** — Add unit tests for `_translate_storage_devices()`: empty `devices` tuple, one NVMe `BlockDevice`, one SATA `BlockDevice`, multiple devices, a device with `size_bytes=None`/`model=None`, and (once 3.1.1's open question is resolved) a `loop`/`rom`-type device to lock in whatever filtering decision was made.
- [ ] **3.4.4** — Add `test_orchestrator_supplies_storage_instead_of_collector` (mirrors `test_orchestrator_supplies_cpu_memory_network_instead_of_collectors`).
- [ ] **3.4.5** — Add `test_orchestrator_storage_none_falls_back_to_collector` (mirrors `test_orchestrator_cpu_none_falls_back_to_collector`) — covers both an unwired `storage` slot and, separately, an isolated `PlatformError` (mirrors `test_orchestrator_cpu_platform_error_falls_back_to_collector`) — two scenarios, consider two tests rather than one to keep each independently reviewable.
- [ ] **3.4.6** — Extend `test_orchestrator_is_called_exactly_once` to also assert a wired storage adapter's `call_count == 1` (optional but recommended — keeps this test's coverage proportional to the number of orchestrator-aware fields).
- [ ] **3.4.7** — Add an end-to-end-style test in `test_commands_inventory.py` (new, not an extension) proving `run_inventory()` actually passes `runtime.host_discovery_orchestrator` through — e.g. a fake orchestrator whose `.discover()` is a `_CountingAdapter`-style spy, asserting it was called once when `run_inventory()` runs. This is the one gap none of the other tests close: `test_inventory_service.py`'s tests call `collect_host_inventory()` directly with a hand-built orchestrator; nothing currently proves `run_inventory()` itself supplies `runtime.host_discovery_orchestrator` rather than, say, always passing `None`.
- [ ] **3.4.8** — Full regression run (`ruff check`, `ruff format --check`, `mypy`, `pytest`) after every one of the above, not just at the end — see [§ 6](#6-risk-assessment) for why this matters more than usual for 3.2.1-3.2.3.

### 3.5 Documentation

See [§ 5](#5-documentation-checklist) for the full list and exact reasoning; checklist form:

- [ ] **3.5.1** — `docs/HOST_DISCOVERY_ORCHESTRATOR.md` status banner and § Relationship to Host Inventory.
- [ ] **3.5.2** — `docs/IMPLEMENTATION_STATUS.md` §5 Host Discovery Status, §8 Outstanding Work, Architecture Components table (Host Inventory row).
- [ ] **3.5.3** — `docs/KNOWN_LIMITATIONS.md` "Host Discovery Orchestrator Not Consumed by Any Command" entry.
- [ ] **3.5.4** — `docs/HOST_INVENTORY.md` § Current Implementation Status table and § service-orchestration description.
- [ ] **3.5.5** — `CHANGELOG.md` new `[Unreleased]` entry (code + tests this time, not documentation-only).
- [ ] **3.5.6** — Close out issue #70's own acceptance-criteria checkboxes; do **not** edit `docs/REAL_WORLD_VALIDATION.md` (it is a fixed historical record by its own stated policy — re-validation belongs in `docs/VM_TEST_LOG.md` as a new entry, not as an edit to that document).

## 4. Test Suite Review

### 4.1 Tests that already protect this code today

| Test | File | What it currently proves | Effect of this change |
|---|---|---|---|
| `test_collect_host_inventory_assembles_all_sections` | `test_inventory_service.py` | All nine collector outputs (including `collect_storage`) assemble correctly with no orchestrator | **Unaffected** — this is the `orchestrator=None`/omitted path, untouched by this issue |
| `test_collect_host_inventory_runs_on_real_host_without_crashing` | `test_inventory_service.py` | Real (unmocked) collectors don't crash | **Unaffected** — no orchestrator involved |
| `test_orchestrator_none_behaves_exactly_like_omitting_it` | `test_inventory_service.py` | `orchestrator=None` explicit ≡ omitted | **Unaffected** — doesn't assert on `storage` at all |
| `test_orchestrator_supplies_cpu_memory_network_instead_of_collectors` | `test_inventory_service.py` | The exact pattern this issue extends to `storage` | **Unaffected**, but is the template for 3.4.4 |
| `test_orchestrator_other_sections_unaffected` | `test_inventory_service.py` | Explicitly asserts `storage` is orchestrator-independent | **Breaks its own claim, not the test itself** (its fixture leaves the `storage` slot unset, so the assertion happens to still pass mechanically) — but the claim becomes false and must be corrected (3.4.2), or this test silently stops meaning what it says |
| `test_orchestrator_is_called_exactly_once` | `test_inventory_service.py` | Each wired adapter is called exactly once | **Unaffected** as written (doesn't wire a storage adapter); extend per 3.4.6 |
| `test_orchestrator_cpu_none_falls_back_to_collector` / `..._memory_none_...` / `..._cpu_platform_error_...` | `test_inventory_service.py` | The exact fallback shape `storage` must replicate | **Unaffected**, template for 3.4.5 |
| `test_orchestrator_unexpected_exception_propagates_unchanged` | `test_inventory_service.py` | A non-`PlatformError` from an adapter is not swallowed | **Unaffected** — generic, not field-specific |
| `test_run_inventory_returns_zero` / `..._text_mentions_key_facts` / `..._json_matches_model` / `..._yaml_output` | `test_commands_inventory.py` | `run_inventory()`'s output rendering in all three formats | **Breaks** (all four) via the shared `patched_inventory` fixture's zero-arg lambda — see 3.4.1. Fix is mechanical (one line), not a design change. |
| Anything in `test_commands_doctor.py` | `test_commands_doctor.py` | `bcs doctor`'s checks, including `storage`/`esp` | **Unaffected** — confirmed `doctor` tests patch `collect_storage` directly, never `collect_host_inventory` |

### 4.2 Tests that must be extended (not new files, new cases in existing files)

- `test_inventory_service.py`: add storage-specific cases alongside the existing `cpu`/`memory` ones (3.4.4, 3.4.5, 3.4.6) — same file, same style, same fixtures (`_CountingAdapter`, `_patch_non_discovery_collectors` — note `_patch_non_discovery_collectors` must also lose its `collect_storage` patch once `storage` is no longer unconditionally collector-sourced in the orchestrator-given branch; check whether any test relying on it now needs its own explicit `collect_storage` patch instead).
- `test_commands_inventory.py`: `patched_inventory` fixture fix (3.4.1) plus one new test (3.4.7).

### 4.3 New regression tests required

- Unit tests for `_translate_storage_devices()` itself (3.4.3) — this is genuinely new code with no existing test to extend.
- `test_orchestrator_supplies_storage_instead_of_collector` / `test_orchestrator_storage_none_falls_back_to_collector` / a `PlatformError`-isolation variant (3.4.4, 3.4.5) — new test functions, though following an exact, already-proven template.
- The `run_inventory()`-passes-the-real-orchestrator-through test (3.4.7) — this specific gap (CLI layer → service layer wiring, as opposed to service layer logic alone) has no existing analog anywhere in the suite today, for *any* field, not just `storage`. Worth naming clearly since it's easy to consider "covered" by the service-layer tests when it isn't.

No new fixture corpus files are needed — this is Host Inventory/service-layer wiring, not Platform Layer adapter parsing; nothing here touches `cli/tests/fixtures/`.

## 5. Documentation Checklist

Only documents whose claims become false once this lands. Documents already describing the target end-state accurately (e.g. `docs/STORAGE_ADAPTER.md:237`, already-correct precedent) are not listed.

| Document | What must change | Why |
|---|---|---|
| `docs/HOST_DISCOVERY_ORCHESTRATOR.md` | Status banner's "Not yet implemented" clause and § Relationship to Host Inventory | Both currently say no command consumes the orchestrator / only `cpu`/`memory`/`network` are sourced from it; `storage` joins that list |
| `docs/IMPLEMENTATION_STATUS.md` | §5 Host Discovery Status "Current limitations" bullet (the storage-specific one added after the real-world validation); §8 Outstanding Work (High) item; §2 Architecture Components' Host Inventory row note ("Does not yet consume the Host Discovery Orchestrator's output") | These were written *describing this exact gap*; they become stale the moment it closes for `storage` (they remain accurate for the still-open `identity`/`firmware`/`efi_system_partition`/`usb_storage`/`tooling` fields, so needs a precise edit, not a blanket "resolved") |
| `docs/KNOWN_LIMITATIONS.md` | "Host Discovery Orchestrator Not Consumed by Any Command" entry's Impact/Confirmed-real-world-symptom text | Currently names `storage_topology` as an example of a fact "collected but never reach[ing] any command output" — no longer true for `storage` specifically |
| `docs/HOST_INVENTORY.md` | § Current Implementation Status table's "Service orchestration" row ("`collect_host_inventory()` calls all nine collectors") | Becomes imprecise — it now *conditionally* calls `collect_storage()`, not unconditionally; the sequence diagram at ~line 245-246 has the same staleness (lower priority — diagrams are more expensive to keep perfectly current, and the prose table is the higher-value fix) |
| `CHANGELOG.md` | New `[Unreleased]` entry | Per `AGENTS.md § Definition of Done` — this is the one entry in this list that is process-mandatory, not optional |
| Issue [#70](https://github.com/nino79/batoi-classroom-suite/issues/70) itself | Check off each Acceptance Criteria box as it's satisfied; close on merge | Standard issue hygiene, not a doc file |

**Explicitly not touched:** `docs/REAL_WORLD_VALIDATION.md` (fixed historical record, by its own stated policy — see that document's own header), `docs/STORAGE_ADAPTER.md` (already accurately anticipates this split, needs no correction), issue #71 (unaffected — still describes a genuinely separate, not-yet-started piece of work), `docs/decisions/0011-host-discovery-orchestrator.md` (per [§ 2](#2-adr-review), no ADR change needed; its Consequences section's "Implemented (Parts 1-4)" bullet remains accurate as a historical record of what Parts 1-4 shipped — this issue is not "Part 5" of that ADR's own implementation, just a further application of the pattern it already approved, so amending the ADR's own text would overstate what changed).

## 6. Risk Assessment

| Task | Risk | Why |
|---|---|---|
| 3.1.1 Translation function | **Medium** | The one genuinely new piece of logic in this issue. The open `device_type` filtering question (loop/rom devices) is a real correctness decision with no existing test to copy — get it wrong and `bcs inventory` silently starts reporting devices it never did before, the opposite failure mode of the bug this issue fixes. |
| 3.1.2 New import (`bcs.platform.adapters.storage.models`) | **Low** | Mechanical; layering direction already established by precedent (`bcs.inventory.discovery.models` does the identical import today). |
| 3.2.1-3.2.3 Service-layer wiring | **Medium** | Structurally identical to the already-proven `cpu`/`memory` pattern (low risk on its own), but this is the code path every existing `test_inventory_service.py` test exercises — a mistake here has the largest blast radius of any single edit in this issue. Mitigated by 3.4.8's "test after every step" discipline. |
| 3.2.4 Docstring update | **Low** | No behavior risk; risk is purely "forgets to do it," which is a documentation-drift bug the project has hit before (see `docs/PATTERNS.md § Common Mistakes`) — listed explicitly so it isn't missed. |
| 3.3.1 CLI wiring | **Low** | One line, mechanical, but is the change that makes 3.4.1's fixture break — sequence matters: land 3.2.x first, confirm the service layer alone is correct, then flip this switch last so any failure is attributable to one change at a time. |
| 3.4.1 Fix `patched_inventory` fixture | **Low** | Mechanical one-line fix, but **High consequence if skipped** — without it, four existing tests fail immediately and would be the first (misleading) signal anyone implementing this sees, potentially causing time lost debugging the wrong layer. |
| 3.4.2 Trim `test_orchestrator_other_sections_unaffected` | **Low** | Mechanical; the test doesn't functionally fail without this (per the analysis in §4.1), so it's easy to skip — but skipping it leaves a false claim in the test suite's own documentation, exactly the kind of drift this project's own review culture (`docs/PATTERNS.md`) flags as a real, recurring mistake category. |
| 3.4.3-3.4.7 New/extended tests | **Low** | Each mirrors an exact, already-proven template in the same file; the risk is omission (forgetting one of the five), not difficulty. |
| 3.5.x Documentation | **Low** | No functional risk; risk is scope (over-editing docs beyond what changed) or omission (under-editing, leaving stale claims) — this checklist's own §5 table exists specifically to bound both. |
| **Overall issue** | **Medium** | Concentrated almost entirely in 3.1.1's open design question and the blast radius of 3.2.1-3.2.3 touching the most heavily-tested function in the module — not in volume of work, which is genuinely small. |

## 7. Explicitly Not Part of This Checklist

Per issue #70's own **Out of scope** section and this task's constraints: no code is written here, no ADR is drafted (§2 concluded none is needed), no test is written (only identified), and nothing beyond `storage` is planned. Identity/firmware/efi_system_partition/usb_storage/tooling wiring, `bcs doctor` integration, and the full legacy-collector deprecation arc remain tracked in [#71](https://github.com/nino79/batoi-classroom-suite/issues/71) and [#78](https://github.com/nino79/batoi-classroom-suite/issues/78) respectively, not here.
