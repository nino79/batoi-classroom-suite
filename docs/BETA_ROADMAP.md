# Beta Roadmap — Batoi Classroom Suite (BCS)

**Phase:** Beta (Phase 0 → Phase 1 transition)
**Based on:** Alpha completion, first successful end-to-end execution on Ubuntu 24.04 VirtualBox VM, observed limitations, and documented architecture.
**Status legend:** ⏳ Planned · 🚧 In progress · ✅ Done

---

## Objectives

1. **Close the gap between architecture and CLI output.** The Host Discovery Orchestrator — fully built, wired, and tested — must be consumed by `bcs inventory` and `bcs doctor` so adapter-sourced facts actually reach the user.
2. **Fix all observed functional defects.** The empty `storage` array (observed on the first VM run) and the `UNKNOWN`-always Secure Boot collector must be resolved before physical hardware validation can be meaningful.
3. **Validate on real LliureX 23 hardware.** A VirtualBox VM proves the CLI installs and runs. Physical NVMe/UEFI machines — especially the target LliureX 23 platform — prove it works where it matters.
4. **Deliver a stable, documented CLI surface.** All four implemented commands (`version`, `validate`, `inventory`, `doctor`) must produce correct, deterministic output on every required target environment. Error messages must be actionable. Known limitations must be documented, not discovered by testers.
5. **Retire or document every legacy collector.** By the end of Beta, every legacy `bcs.inventory.collectors` function either routes through the Host Discovery pipeline, or has a documented ADR-backed reason for staying as-is.

---

## Milestones

### M1 — Storage Collector Fix & Baseline

**Goal:** `bcs inventory` reports real storage devices on a VirtualBox VM, and the first full validation pass on E01 is complete.

| Item | Effort | Dependencies | Status |
|---|---|---|---|
| Diagnose and fix `collect_storage()` — the current glob `nvme[0-9]n[0-9]` matches `/dev/nvme0n1` but the real VM (SATA controller) exposes `/dev/sda`. The glob returns empty for non-NVMe names. Decision: either extend the glob to `/dev/sd*` or declare this a known limitation pending NVMe-only support (PLAT-005). | Small | Root-cause analysis (in progress) | ⏳ |
| Run the full `BETA_RELEASE_CHECKLIST.md` on E01 and log results in `VM_TEST_LOG.md`. | Small | Storage fix | ⏳ |
| Capture real `efibootmgr`, `lsblk`, `blkid`, `findmnt`, `mokutil` output from the VM into `cli/tests/fixtures/{firmware,storage,secureboot,filesystem,network}/`. | Small | Storage fix | ⏳ |
| Update `KNOWN_LIMITATIONS.md` with the SATA-vs-NVMe limitation if the fix is deferred. | Trivial | Decision outcome | ⏳ |

**Exit criteria:**
- [ ] `bcs inventory` shows storage devices on E01 (VirtualBox with any disk controller).
- [ ] All 27 `VM_VALIDATION.md` test cases pass on E01.
- [ ] At least one fixture capture is committed per domain.

---

### M2 — Host Discovery Orchestrator Consumption

**Goal:** `bcs inventory` and `bcs doctor` consume the `HostDiscoverySnapshot` for `network`, `cpu`, `memory`, and `caveats`.

This is the single highest-impact engineering item in Beta. The wiring exists (`RuntimeContext.host_discovery_orchestrator`, `collect_host_inventory(orchestrator=...)`); it simply is not being used by any command.

#### 2a — Wire `bcs inventory` to pass the orchestrator through

| Item | Effort | Dependencies | Status |
|---|---|---|---|
| Modify `run_inventory()` in `cli/src/bcs/commands/inventory.py` (line 135) to pass `runtime.host_discovery_orchestrator` into `collect_host_inventory(orchestrator=...)`. | Trivial | None | ⏳ |
| Add/update tests in `cli/tests/test_commands_inventory.py` verifying the orchestrator is invoked when present and not invoked when absent. | Small | Code change | ⏳ |
| Verify `bcs inventory --output json` output is byte-for-byte identical with and without the orchestrator on E01 (the VM has the same collectors either way). | Small | Code change | ⏳ |

**Exit criteria:**
- [ ] `bcs inventory` calls `runtime.host_discovery_orchestrator.discover()` exactly once per invocation.
- [ ] Existing tests pass unchanged. New tests cover the orchestrator-present path.
- [ ] Output on E01 is regression-free (same fields, same values).

#### 2b — Wire `bcs doctor` to consume the orchestrator for `secure-boot`, `network`, `caveats`

| Item | Effort | Dependencies | Status |
|---|---|---|---|
| Refactor `_check_secure_boot()` in `cli/src/bcs/commands/doctor.py` to prefer `orchestrator.discover().secure_boot` over `collect_firmware().secure_boot` when an orchestrator is available. | Small | M2a | ⏳ |
| Refactor `_check_network()` to prefer `orchestrator.discover().network` over `collect_network()`. | Small | M2a | ⏳ |
| Add a new `discovery` check (or fold `caveats` into an existing check) surfacing any adapter-caught `PlatformError` entries. | Medium | M2a, design decision | ⏳ |
| Add tests covering orchestrator-sourced checks, fallback-to-collector paths, and caveats rendering. | Medium | Code changes | ⏳ |

**Exit criteria:**
- [ ] `bcs doctor --check secure-boot` reports real state (not `UNKNOWN`) when `mokutil` is present.
- [ ] `bcs doctor --check network` reports IP addresses when the Network Adapter is wired (see M3).
- [ ] `bcs doctor` includes a visible caveats section when adapters report errors.
- [ ] All existing 211 lines of `doctor.py` tests pass.

#### 2c — ADR-0008 amendment for Discovery-domain schema folding

| Item | Effort | Dependencies | Status |
|---|---|---|---|
| Write an ADR-0008 amendment proposing `firmwareBootConfiguration`, `storageTopology`, `secureBoot`, `filesystemUsage`, `tpm`, and `caveats` as new `HostInventory` fields — per ADR-0011 Decision point 6. | Medium | ADR process | ⏳ |
| Update `bcs.inventory.models.HostInventory` to include the new fields (if the ADR passes). | Medium | ADR acceptance | ⏳ |
| Update `bcs.inventory.service.collect_host_inventory()` to map snapshot fields into the new schema fields. | Medium | Model changes | ⏳ |
| Update all output renderers (`_print_text`, JSON, YAML) in `bcs.commands.inventory`. | Medium | Schema change | ⏳ |

**Exit criteria:**
- [ ] ADR-0008 amendment accepted.
- [ ] `bcs inventory --output json` includes the new Discovery-domain fields.
- [ ] Backward compatibility: old consumers that ignore unknown fields continue to work.

---

### M3 — Network Adapter Wiring

**Goal:** The Network Adapter replaces `sysfs`-based `collect_network()` in the Host Discovery composition root. IP addresses appear in `bcs inventory`.

| Item | Effort | Dependencies | Status |
|---|---|---|---|
| Complete Network Adapter Parts 2–4 (errors, parser, adapter — already fully implemented per `cli/src/bcs/platform/adapters/network/`). Add dedicated test modules for `errors.py` and `parser.py`. | Small | None (code exists, tests needed) | ⏳ |
| Narrow `HostDiscoveryAdapters.network` / `HostDiscoverySnapshot.network` typing to the adapter's concrete model type. | Trivial | Part 2–4 tests | ⏳ |
| Replace `collectors.collect_network` binding in `bcs.app.main()` line 218 with `functools.partial(read_network_interfaces, runner=command_runner)`. | Trivial | M3 completion | ⏳ |
| Verify `bcs inventory` now includes non-empty `ip_addresses` on E01. | Small | Wiring | ⏳ |
| Update `NETWORK_ADAPTER.md` status banner, `IMPLEMENTATION_STATUS.md` rows, `KNOWN_LIMITATIONS.md` entry. | Trivial | Wiring | ⏳ |

**Exit criteria:**
- [ ] `bcs inventory` shows IP addresses in network section.
- [ ] `bcs doctor --check network` uses `ip` tool data.
- [ ] Network parts in `cli/tests/fixtures/network/` populated with real captures.
- [ ] `KNOWN_LIMITATIONS.md` "Network Adapter Implemented but Not Wired" entry updated to reflect completion.

---

### M4 — Secure Boot Collector Real Implementation

**Goal:** The legacy `_read_secure_boot_state()` returns a real value instead of `UNKNOWN`.

| Item | Effort | Dependencies | Status |
|---|---|---|---|
| Implement `_read_secure_boot_state()` to parse the `SecureBoot-<GUID>` EFI variable's byte value — or, simpler, route `collect_firmware()` through the Secure Boot adapter when no orchestrator is available. | Small | M2b (doctor wiring) | ⏳ |
| Add tests covering enabled, disabled, and variable-absent states. | Small | Code change | ⏳ |
| Update `KNOWN_LIMITATIONS.md` — remove the `UNKNOWN`-always placeholder entry. | Trivial | Code change | ⏳ |

**Exit criteria:**
- [ ] `bcs inventory` reports `secureBoot: enabled` or `secureBoot: disabled` on real UEFI hardware.
- [ ] `bcs doctor --check secure-boot` returns `OK` or `WARN` based on real state (never `UNKNOWN`).

---

### M5 — Physical Hardware Validation

**Goal:** Beta is validated on physical machines, not just VMs.

| Item | Effort | Dependencies | Status |
|---|---|---|---|
| Validate on Ubuntu 24.04 physical NVMe/UEFI, Secure Boot disabled (E02). | Medium | M1, M2a, M4 | ⏳ |
| Validate on Ubuntu 24.04 physical NVMe/UEFI, Secure Boot enabled (E03). | Medium | M2a, M4 | ⏳ |
| Validate on LliureX 23 physical NVMe/UEFI (E06). | Medium | M1, M2a, M4 | ⏳ |
| Update `HARDWARE_VALIDATION_MATRIX.md` with real results for each environment. | Small | Each validation session | ⏳ |
| Report P0/P1 bugs found; triage against `KNOWN_LIMITATIONS.md`. | Ongoing | Validation sessions | ⏳ |

**Exit criteria:**
- [ ] `bcs doctor` passes on E02–E06 per `HARDWARE_VALIDATION_MATRIX.md` expectations.
- [ ] `bcs inventory --output json` is parseable on every environment.
- [ ] No P0 bugs remain open.
- [ ] E06 (LliureX 23) shows `tooling: OK` for Clonezilla/Partclone.

---

### M6 — Infrastructure & Quality-of-Life

**Goal:** Developer and tester friction is reduced. CI, fixtures, and test infrastructure are ready for the next phase.

| Item | Effort | Dependencies | Status |
|---|---|---|---|
| Implement shared `FakeCommandRunner` test double under `cli/tests/` and migrate existing adapter tests. | Medium | None | ⏳ |
| Capture real hardware/VM output into `cli/tests/fixtures/{firmware,storage,secureboot,filesystem,network}/`, replacing zero-byte placeholders. | Medium | M1 (first captures) | ⏳ |
| Extend `cli-smoke-test` CI job to run `bcs doctor` and `bcs inventory` in addition to `bcs version`. | Small | None | ⏳ |
| Narrow `cli/pyproject.toml` Bandit `S603`/`S607` scoping from repository-wide to `bcs.plugins`/`bcs.platform.execution` only. | Trivial | None | ⏳ |
| Consolidate `FrozenModel`/`FrozenExtensibleModel` into `bcs.model_utils`. | Small | None | ⏳ |

**Exit criteria:**
- [ ] All adapter test suites use shared `FakeCommandRunner`.
- [ ] At least one real fixture file per domain is committed.
- [ ] CI smoke-test runs `doctor` and `inventory`.
- [ ] `ruff check .` enforces `S603`/`S607` scope correctly.

---

### M7 — Documentation & Release Engineering

**Goal:** Documentation reflects Beta state. The repository is ready for tagging a Beta release.

| Item | Effort | Dependencies | Status |
|---|---|---|---|
| Update `docs/README.md`, `IMPLEMENTATION_STATUS.md`, `KNOWN_LIMITATIONS.md` to reflect all Beta changes. | Medium | M1–M6 | ⏳ |
| Update `docs/CLI.md` line 98 stale ADR-0009 reference. | Trivial | None | ⏳ |
| Resolve VM documentation inconsistencies (VM name mismatch, duplicate instructions, etc. — see `BETA_PREPARATION_REPORT.md`). | Medium | None | ⏳ |
| Version bump in `cli/pyproject.toml` to a Beta semver (e.g. `0.2.0-beta.1`). | Trivial | M1–M6 | ⏳ |
| Write `CHANGELOG.md` `[Unreleased]` entries for every Beta change. | Medium | M1–M6 | ⏳ |
| Tag and publish a Beta release (git tag + GitHub Release). | Trivial | All above | ⏳ |

**Exit criteria:**
- [ ] All documentation inconsistencies identified in `BETA_PREPARATION_REPORT.md` are resolved.
- [ ] `CHANGELOG.md` has complete Beta entries.
- [ ] A Beta release is tagged in git and published to GitHub.

---

## Priorities

| Priority | Label | Items |
|---|---|---|
| P0 — Blocking | 🔴 | M1 (storage fix), M2a (HDO → inventory) |
| P1 — High | 🟠 | M2b (HDO → doctor), M2c (ADR-0008 amendment), M4 (Secure Boot real impl), M5 (physical validation) |
| P2 — Medium | 🟡 | M3 (Network Adapter wiring), M6 items (shared FakeCommandRunner, CI smoke-test) |
| P3 — Low | 🔵 | M7 (documentation cleanup, VM doc inconsistencies) |

---

## Dependencies Map

```
M1 (storage fix) ──────────────────────────────────────┐
                                                        │
M2a (HDO → inventory) ─── M2b (HDO → doctor) ──────────┤
                              │                         │
                              └── M2c (ADR amendment) ──┤
                                                        │
M3 (Network Adapter wiring) ────────────────────────────┤
                                                        │
M4 (Secure Boot real impl) ─────────────────────────────┤
                                                        │
                                              ┌─────────┘
                                              ▼
M5 (physical hardware validation) ─── M6 (infrastructure)
                                              │
                                              ▼
                                      M7 (release)

M1 has no dependencies (the fix itself is independent).
M2a depends on nothing but a small code change.
M2b depends on M2a (the orchestrator must be passed through first).
M2c is conceptually independent of M2b but affects the same model.
M3 is independent of M2 (parallel track).
M4 interacts with M2b (doctor wiring).
M5 depends on M1, M2a, M4 being stable.
M6 is independent (parallel track throughout).
M7 depends on everything above.
```

---

## Estimated Effort

| Milestone | Engineering | Testing | Documentation | Calendar estimate (sequential) |
|---|---|---|---|---|
| M1 — Storage fix & baseline | 0.5 day | 0.5 day | 0.5 day | 1–2 days |
| M2a — HDO → inventory | 0.5 day | 0.5 day | 0.5 day | 1–2 days |
| M2b — HDO → doctor | 1 day | 1 day | 0.5 day | 2–3 days |
| M2c — ADR-0008 amendment | 1 day | 1 day | 1 day | 2–3 days |
| M3 — Network Adapter wiring | 1 day | 1 day | 0.5 day | 2–3 days |
| M4 — Secure Boot impl | 0.5 day | 0.5 day | 0.5 day | 1–2 days |
| M5 — Physical validation | 2 days (3 env × 0.5 d + buffer) | — | 1 day | 4–5 days* |
| M6 — Infrastructure | 2 days | 1 day | 0.5 day | 3–4 days |
| M7 — Release | 0.5 day | 0.5 day | 1 day | 1–2 days |
| **Total (sequential)** | **9 days** | **6 days** | **6 days** | **~17–26 days** |
| **Total (parallelized)** | — | — | — | **~10–14 days** |

\* Physical validation depends on hardware availability and is inherently sequential across environments. M5 runs in parallel with M6.

---

## Collector Deprecation Plan

By the end of Beta, every `bcs.inventory.collectors` function has one of three fates:

| Collector | Fate | Beta Milestone | Notes |
|---|---|---|---|
| `collect_firmware()` | **Kept** — feeds `HostInventory.firmware`. Secure Boot sub-function (`_read_secure_boot_state`) reimplemented or replaced. | M4 | The UEFI-probe half stays; Secure Boot half is replaced by adapter data. |
| `collect_storage()` | **Kept** — feeds `HostInventory.storage`. Glob pattern may be extended. | M1 | NVMe-only is spec-compliant (PLAT-005) but SATA detection improves UX. |
| `collect_efi_system_partition()` | **Kept** — feeds `HostInventory.efiSystemPartition`. No adapter planned. | — | Adequate for current requirements. |
| `collect_usb_storage()` | **Kept** — feeds `HostInventory.usbStorage`. No adapter planned. | — | Adequate. Schema boundary ambiguity (boot USB appearing in both `storage` and `usbStorage`) tracked as known limitation. |
| `collect_identity()` | **Kept** — feeds `HostInventory.identity`. No adapter planned. | — | Stdlib-only DMI/MAC reads. |
| `collect_operating_system()` | **Kept** — feeds `HostInventory.operatingSystem`. No adapter planned. | — | Single `/etc/os-release` read. |
| `collect_cpu()` | **Migrated** — via HDO snapshot when available; kept as fallback. | M2a | Falls back to collector when adapter slot is `None` (already implemented in `service.py`). |
| `collect_memory()` | **Migrated** — via HDO snapshot when available; kept as fallback. | M2a | Same fallback pattern as CPU. |
| `collect_network()` | **Deprecated** — replaced by Network Adapter. | M3 | Still callable directly but no longer the primary path after M3. |
| `collect_tooling()` | **Kept** — feeds `HostInventory.tooling`. No adapter planned. | — | Adequate. |

---

## Definition of Done for Beta

Beta is complete when **all** of the following hold:

- [ ] **M1 complete.** Storage array is non-empty on E01. Baseline validation pass logged.
- [ ] **M2a complete.** `bcs inventory` consumes the Host Discovery Orchestrator.
- [ ] **M2b complete.** `bcs doctor` consumes the orchestrator for `secure-boot`, `network`, and caveats.
- [ ] **M2c accepted.** ADR-0008 amendment for Discovery-domain schema folding is either accepted with implementation underway, or explicitly deferred to Phase 1 with documented reasoning.
- [ ] **M3 complete.** Network Adapter is wired. IP addresses appear in inventory output.
- [ ] **M5 complete.** Physical validation on E02, E03, and E06 is logged in `VM_TEST_LOG.md`.
- [ ] **No P0 or P1 bugs** remain open in the Beta issue tracker.
- [ ] **`KNOWN_LIMITATIONS.md`** reflects the current state (no stale entries from Alpha).
- [ ] **`IMPLEMENTATION_STATUS.md`** is updated for every code change.
- [ ] **`CHANGELOG.md`** has complete `[Unreleased]` entries for the Beta phase.
- [ ] **A Beta release tag** exists (e.g. `v0.2.0-beta.1`).
- [ ] **`ruff check`, `ruff format --check`, `mypy`, `pytest`** all pass on the release commit.
- [ ] **CI is green** on the release commit.

---

## Candidate Beta Release Criteria

A Beta release may be cut early if the following minimum criteria are met (as a "Beta preview" before all items are complete):

| Tier | Criteria | Tag example |
|---|---|---|
| **Beta preview** | M1 + M2a complete. Storage works, HDO consumed by inventory. | `v0.2.0-beta.1` |
| **Beta RC1** | M1 + M2a + M2b + M4. Full CLI pipeline working with correct data. | `v0.2.0-rc.1` |
| **Beta RC2** | Above + M3 + M5. Physical hardware validated. | `v0.2.0-rc.2` |
| **Beta final** | All items above + M6 + M7. Docs, fixtures, CI, release engineering complete. | `v0.2.0` |

The release committee should decide at each RC whether to cut the next RC or proceed to final.

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Storage collector fix reveals deeper `lsblk`/`blkid` parsing gap | Low | Medium | M1 scope is limited to the legacy collector glob pattern; the Storage Adapter pipeline already handles real hardware output. |
| ADR-0008 amendment is rejected or deferred | Medium | High (M2c) | If rejected, the Discovery-domain schema gap remains documented in `KNOWN_LIMITATIONS.md` and is deferred to Phase 1. |
| Physical hardware (E02/E03/E06) unavailable | Medium | High (M5) | Cannot be mitigated by the project itself; engage CIPFP Batoi early. NVMe-to-USB adapter + any UEFI PC is a fallback. |
| Network Adapter wiring reveals real-hardware `ip` output variations not covered by synthetic tests | Low | Medium | Mitigated by fixture capture (M6). Running on E01 first catches VirtualBox-specific issues. |
| Secure Boot variable parsing on physical hardware reveals firmware-specific byte layouts | Low | Medium | Mitigated by the simpler approach: route through the existing adapter path (M2b) instead of parsing efivars directly. |

---

## Related Documents

- [BETA_VALIDATION_PLAN.md](BETA_VALIDATION_PLAN.md) — the validation process for this roadmap's output
- [BETA_RELEASE_CHECKLIST.md](BETA_RELEASE_CHECKLIST.md) — per-release verification items
- [HARDWARE_VALIDATION_MATRIX.md](HARDWARE_VALIDATION_MATRIX.md) — per-environment expected results
- [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md) — limitations this roadmap aims to reduce
- [BETA_PREPARATION_REPORT.md](BETA_PREPARATION_REPORT.md) — pre-Beta baseline audit
- [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) — current-state dashboard
- [ROADMAP.md](../ROADMAP.md) — the long-term project roadmap (Phase 0 → v1.0)
- [NETWORK_ADAPTER_IMPLEMENTATION_PLAN.md](NETWORK_ADAPTER_IMPLEMENTATION_PLAN.md) — detailed parts breakdown for M3
- [HOST_DISCOVERY_ORCHESTRATOR.md](HOST_DISCOVERY_ORCHESTRATOR.md) — the orchestrator M2 integrates with
- [PATTERNS.md](PATTERNS.md) — the adapter-building process used by M3
