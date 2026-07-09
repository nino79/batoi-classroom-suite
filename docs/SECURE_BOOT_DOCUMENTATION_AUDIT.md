# Secure Boot Documentation Audit — Beta M4 Preparation

**Purpose:** For every document in the repository that mentions Secure Boot (or any
related term — `mokutil`, `PLAT-004`, `UEFI` in a Secure Boot context, `secure_boot`,
`_read_secure_boot_state()`, `SecureBootState.UNKNOWN`), determine whether the
document will become outdated when the Beta M4 Secure Boot implementation lands,
and what action, if any, is needed before or after that change.

**Scope:** Top-level `.md` files, `docs/` (all subdirectories), ADRs, reports,
design documents, and `config/schema.yaml`. Python source and test files are
excluded per the stated task scope.

**M4 scope (from `BETA_ROADMAP.md`):**
The legacy `_read_secure_boot_state()` returns a real value instead of `UNKNOWN`.
Two approaches are under consideration: (a) parse the `SecureBoot-<GUID>` EFI
variable's byte value, or (b) route `collect_firmware()` through the existing
Secure Boot adapter when no orchestrator is available. The roadmap expresses a
preference for (b) — "the simpler approach: route through the existing adapter
path (M2b) instead of parsing efivars directly."

---

## A. Cross-Reference Report

### A.1 Top-Level Documents

#### 1. `README.md`

| Section | Current Wording | Outdated After M4? | Recommendation |
|---|---|---|---|
| Target Platform table | `Firmware \| UEFI (Secure Boot aware)` | No — still correct | KEEP |
| Documentation index | `docs/SECURE_BOOT_ADAPTER.md … fully implemented` | No — still correct | KEEP |

No changes needed.

---

#### 2. `SPECIFICATION.md`

| Section | Current Wording | Outdated After M4? | Recommendation |
|---|---|---|---|
| §1 Target Platform Matrix | `PLAT-004: UEFI Secure Boot must be either supported or safely, explicitly disabled as part of deployment — silent incompatibility is not acceptable.` | No — requirement unchanged | KEEP |

No changes needed.

---

#### 3. `ARCHITECTURE.md`

| Section | Current Wording | Outdated After M4? | Recommendation |
|---|---|---|---|
| §5 Cross-Cutting Concerns | `UEFI Secure Boot compatibility is a first-class constraint on Boot Manager.` | No — still correct | KEEP |

No changes needed.

---

#### 4. `SECURITY.md`

| Section | Current Wording | Outdated After M4? | Recommendation |
|---|---|---|---|
| Boot integrity | `Boot Manager's interaction with UEFI Secure Boot and its fallback behavior (SPEC BM-005)` | No — still correct | KEEP |

No changes needed.

---

#### 5. `AGENTS.md`

| Section | Current Wording | Outdated After M4? | Recommendation |
|---|---|---|---|
| Project Orientation | `read-only hardware-discovery adapters (EFI, Storage, and Secure Boot all fully implemented and wired into the Host Discovery Orchestrator's composition root` | No — still correct | KEEP |

No changes needed.

---

#### 6. `CHANGELOG.md`

| Section | Current Wording | Outdated After M4? | Recommendation |
|---|---|---|---|
| v0.1.2 changelog entries | Multiple entries describing Secure Boot Adapter acceptance, full implementation, and composition-root wiring. | No — historical accuracy | KEEP |
| Host Inventory subsystem description | `immutable, extensible Pydantic models (HostInventory and its sections — firmware/Secure Boot, storage, ...)` | No — still correct | KEEP |

No changes needed.

---

#### 7. `ROADMAP.md`

| Section | Current Wording | Outdated After M4? | Recommendation |
|---|---|---|---|
| Phase 0 tracker | `Secure Boot Adapter … fully implemented \| ✅` | No — still correct | KEEP |
| Phase 1 (Boot Manager) | `⏳ Secure Boot compatibility assessment` | No — Phase 1 | KEEP |
| Phase 2 (Builder) | `💤 UEFI Secure Boot signing pipeline for Builder output` | No — Phase 2 | KEEP |

No changes needed.

---

#### 8. `config/schema.yaml`

| Section | Current Wording | Outdated After M4? | Recommendation |
|---|---|---|---|
| `spec.security.secureBoot.mode` | `PLAT-004: canonical Secure Boot posture. Boot Manager's boot` | No — schema describes desired policy, not observed state | KEEP |

No changes needed.

---

### A.2 `docs/` — Design Documents

#### 9. `docs/SECURE_BOOT_ADAPTER.md`

| Section | Current Wording | Outdated After M4? | Recommendation |
|---|---|---|---|
| Status banner | `Accepted; fully implemented. … Not yet done: folding secure_boot into HostInventory's own schema … and wiring bcs doctor/bcs inventory to actually pass runtime.host_discovery_orchestrator through` | **Partially outdated** — after M2b + M2c + M4, both the folding and the wiring may be done. | **UPDATE** status banner once those steps land. |
| § Purpose | `Host Inventory's own documented gap … FirmwareInfo.secure_boot currently returns unknown … Recorded as a placeholder` | **Outdated after M4** — the gap will be closed. | **UPDATE** § Purpose to remove "gap" framing, replace with "Secure Boot Adapter is the mechanism that closed the documented `FirmwareInfo.secure_boot` placeholder gap." |
| § Purpose | `PLAT-004's own requirement has no observation mechanism today` | **Outdated after M4** — it will have one. | **UPDATE** to "Secure Boot Adapter gives PLAT-004 its observation mechanism." |
| § Scope Guarantee | `This adapter never makes a decision … Comparing an observed fact against a desired policy … is bcs doctor's job` | No — still correct, even after M2b | KEEP |
| § Future Extensibility | `Closing HostInventory's FirmwareInfo.secure_boot placeholder … remains part of the still-open HostInventory schema amendment` | **Outdated after M2c** — the schema amendment should be either accepted or explicitly deferred. | **UPDATE** to reflect the outcome of ADR-0008 amendment (either "done" or "deferred"). |
| § Open Questions | `Whether/how this adapter is wired into bcs doctor — not decided here.` | **Outdated after M2b** — M2b explicitly decides to wire doctor via the orchestrator. | **UPDATE** to "Wired into `bcs doctor` via M2b (orchestrator path in `_check_secure_boot()`)." |
| § Backward Compatibility | no changes to `bcs.inventory.models.SecureBootState` | No — still correct | KEEP |
| § Sequence Diagram (doctor) | `illustrative — not decided by this document` | **Outdated** — the decision is taken. | **UPDATE** to reference M2b, remove the illustrative caveat. |
| § Related Documents | links to SPECIFICATION.md § PLAT-004 | No — still correct | KEEP |

**Total changes needed:** 6 sections updated (status banner, Purpose ×2, Future Extensibility, Open Questions, Sequence Diagram).

---

#### 10. `docs/HOST_DISCOVERY_ORCHESTRATOR.md`

| Section | Current Wording | Outdated After M4? | Recommendation |
|---|---|---|---|
| § Public API — `HostDiscoveryAdapters` table | `secure_boot` slot: `Callable[[], SecureBootStatus] \| None`, wired at composition root | No — still correct | KEEP |
| § Public API — `HostDiscoverySnapshot` table | `secure_boot` slot: `SecureBootStatus \| None`, from the secure_boot slot | No — still correct | KEEP |
| § Relationship to Host Inventory | `This integration does not add firmwareBootConfiguration/storageTopology/secureBoot/etc. as new HostInventory fields` | **Outdated after M2c** — the ADR-0008 amendment may add them. | **UPDATE** to reflect M2c outcome. |
| § Sequence Diagram — doctor secure-boot | `Cmd->>Adapters: read secure_boot` — shows doctor reading from orchestrator | No — this is the desired future state | KEEP (no change; the diagram is already aspirational) |
| § Error Propagation | `A wired secure_boot/filesystem adapter raising a PlatformError (e.g. mokutil/df not found) does get a caveats entry` | No — still correct | KEEP |
| § Future Extensibility | `Secure Boot … already went through this exact process` | No — still correct | KEEP |

**Total changes needed:** 1 section updated (Relationship to Host Inventory, pending M2c).

---

#### 11. `docs/HOST_INVENTORY.md`

| Section | Current Wording | Outdated After M4? | Recommendation |
|---|---|---|---|
| § Pydantic Models — `SecureBootState` enum | Lists `ENABLED, DISABLED, UNSUPPORTED, UNKNOWN` | No — the model doesn't change | KEEP |
| § Responsibilities | `SecureBootState enumerates the only valid answers to "what is this firmware's Secure Boot state"` | No — still correct | KEEP |
| § Open Questions / Explicitly Deferred | `Secure Boot byte-value parsing … currently returns unknown … Recorded as a placeholder` | **Outdated after M4** — the placeholder will be replaced with real implementation. | **UPDATE** to "Resolved — `_read_secure_boot_state()` now returns a real value via the Secure Boot adapter path (Beta M4)." |
| § Sequence Diagram (Boot Manager) | `BM->>BM: decide boot-chain behaviour (PLAT-004, BM-005 fallback)` | No — Boot Manager doesn't exist yet | KEEP |
| § Interaction with CLI — JSON example | `"firmware": {"uefi": true, "secureBoot": "enabled", "vendor": null, "version": null}` | No — this is an example of future output | KEEP (no change; it's aspirational and already correct) |

**Total changes needed:** 1 section updated (Open Questions).

---

#### 12. `docs/EFI_ADAPTER.md`

| Section | Current Wording | Outdated After M4? | Recommendation |
|---|---|---|---|
| § Related Documents | `docs/HOST_INVENTORY.md and ADR-0008 — … FirmwareInfo's existing UEFI/Secure Boot facts this adapter's data is expected to eventually sit alongside.` | No — still correct as aspirational | KEEP |

No changes needed.

---

#### 13. `docs/CONFIGURATION.md`

| Section | Current Wording | Outdated After M4? | Recommendation |
|---|---|---|---|
| `spec.security.secureBoot.mode` table | `PLAT-004: canonical Secure Boot posture. … This is the only place Secure Boot posture is configured` | No — schema unchanged | KEEP |
| Duplication Avoided: `secureBoot` | `Secure Boot posture is a security decision (PLAT-004) that Boot Manager must honor` | No — still correct | KEEP |

No changes needed.

---

#### 14. `docs/CLI.md`

| Section | Current Wording | Outdated After M4? | Recommendation |
|---|---|---|---|
| § `bcs doctor` checks | `secure-boot (state vs. spec.security.secureBoot.mode if a config is loaded)` | No — still correct; the check's logic doesn't change | KEEP |
| § `bcs doctor` example output | `[ WARN] secure-boot Secure Boot is disabled; config requests enforce` | No — still valid example | KEEP |
| Line 98 stale ADR-0009 reference | `(Accepted, not yet implemented)` — refers to Platform Layer | No — unrelated to Secure Boot | Already tracked separately in `KNOWN_LIMITATIONS.md` |

No changes needed.

---

#### 15. `docs/PLATFORM_LAYER.md`

| Section | Current Wording | Outdated After M4? | Recommendation |
|---|---|---|---|
| Abstract | `bcs.inventory.collectors deliberately avoids external tools … with documented placeholder gaps (IP address enumeration, Secure Boot byte-value parsing)` | **Outdated after M4** — the Secure Boot byte-value parsing gap will be closed. The IP address gap was already closed by M3. | **UPDATE** to remove "Secure Boot byte-value parsing" from the list of placeholder gaps. |
| § Approved Design Decisions | Same mention of `bcs.inventory.collectors`' two documented placeholder gaps (IP enumeration, Secure Boot byte-value parsing) | **Outdated after M4** — same as above. | **UPDATE** to remove both gaps (IP already fixed in M3, Secure Boot fixed in M4). |

**Total changes needed:** 2 sections updated.

---

#### 16. `docs/PATTERNS.md`

| Section | Current Wording | Outdated After M4? | Recommendation |
|---|---|---|---|
| § Domain-Driven Naming | `A package is named after the domain concept (secureboot, not mokutil)` | No — still correct | KEEP |

No changes needed.

---

### A.3 `docs/` — Report / Roadmap / Validation Documents

#### 17. `docs/BETA_ROADMAP.md`

| Section | Current Wording | Outdated After M4? | Recommendation |
|---|---|---|---|
| § M4 — Secure Boot Real Implementation | Entire milestone: goal, items, exit criteria | **Will be outdated after M4 done** — changed from `⏳` to `✅`. | **UPDATE** status after M4 lands. Change M4 items from ⏳ to ✅. Update M4's exit criteria from future-tense to past-tense completion statements. |
| § M2b — Doctor wiring | `Refactor _check_secure_boot() … to prefer orchestrator.discover().secure_boot` | No — M2b is a prerequisite for M4 | KEEP (or mark ⏳ after M4) |
| § Objectives | `Fix all observed functional defects. … the UNKNOWN-always Secure Boot collector must be resolved` | **Outdated after M4** — it will be resolved. | **UPDATE** to "Resolved: the Secure Boot collector now returns a real value (M4)." |
| § Dependencies Map | M4 diagram node pointing into M5 | **No** — dependency structure unchanged | KEEP |
| § Collector Deprecation Plan | `collect_firmware() Kept — feeds HostInventory.firmware. Secure Boot sub-function (_read_secure_boot_state) reimplemented or replaced. M4` | No — this is the plan; after M4, mark as done. | **UPDATE** to "`collect_firmware()` Kept. `_read_secure_boot_state()` replaced by adapter path (M4 done)." |
| § Definition of Done — M4 | `M4 (Secure Boot real impl)` | No — still a dependency | KEEP (or mark done) |
| § Risks | `Secure Boot variable parsing on physical hardware reveals firmware-specific byte layouts \| Low \| Medium \| Mitigated by the simpler approach: route through the existing adapter path (M2b) instead of parsing efivars directly.` | **Outdated after M4** — the mitigation was chosen and proven. | **UPDATE** to "Mitigated: M4 chose the adapter-routing approach (M2b). No firmware-specific byte-layout issues observed." |
| § Estimated Effort | M4: 0.5 day engineering, 0.5 day testing, 0.5 day documentation | **Outdated after M4** — actual effort known. | **UPDATE** to actual effort. |

**Total changes needed:** 5 sections updated after M4 completion.

---

#### 18. `docs/BETA_VALIDATION_PLAN.md`

| Section | Current Wording | Outdated After M4? | Recommendation |
|---|---|---|---|
| Scope | `Cross-environment validation: VirtualBox, physical hardware, Secure Boot on/off, storage backends` | No — still correct | KEEP |
| Environment table | `| ID | Environment | Storage | Firmware | Secure Boot | Priority |` | No — the table is unchanged | KEEP |

No changes needed.

---

#### 19. `docs/BETA_PREPARATION_REPORT.md`

| Section | Current Wording | Outdated After M4? | Recommendation |
|---|---|---|---|
| Key Findings | `Host Discovery adapters (4 fully implemented): … Secure Boot` | No — still correct | KEEP |
| Key Findings | `Secure Boot collector returns placeholder UNKNOWN \| Medium` | **Outdated after M4** — the placeholder will be resolved. | **UPDATE** to "Resolved — Secure Boot collector now returns real value (M4)." |
| Documentation | `KNOWN_LIMITATIONS.md: Updated: added … Secure Boot collector placeholder` | **Outdated after M4** — KNOWN_LIMITATIONS will remove that entry. | **UPDATE** to "KNOWN_LIMITATIONS.md: Removed `_read_secure_boot_state()` placeholder entry (M4)." |
| Implementation Status | `Adapter designs (4): Secure Boot — Accepted, implemented` | No — still correct | KEEP |

**Total changes needed:** 2 sections updated.

---

#### 20. `docs/BETA_RELEASE_CHECKLIST.md`

| Section | Current Wording | Outdated After M4? | Recommendation |
|---|---|---|---|
| Validation items | `Validated on Ubuntu 24.04 physical, NVMe, UEFI, Secure Boot disabled (E02)` | No — checklist items are pre-flight | KEEP |
| Validation items | `Validated on Ubuntu 24.04 physical, NVMe, UEFI, Secure Boot enabled (E03)` | No — same reasoning | KEEP |

No changes needed.

---

#### 21. `docs/KNOWN_LIMITATIONS.md`

| Section | Current Wording | Outdated After M4? | Recommendation |
|---|---|---|---|
| § Host Discovery Orchestrator Not Consumed by `bcs doctor` | `Tool-detection facts that would come from adapters (e.g. mokutil not found) are not surfaced to the user via bcs doctor.` | **Outdated after M2b** — doctor will use the orchestrator. | **UPDATE** to reflect M2b completion (doctor now consumes orchestrator, caveats visible). |
| § Host Inventory Schema Does Not Include Discovery-Domain Facts | `secure_boot … lives on HostDiscoverySnapshot but are never folded into HostInventory's own schema` | **Outdated after M2c** — if the ADR-0008 amendment passes, this will be resolved. If not, it remains. | **UPDATE** to reflect M2c outcome. |
| § `_read_secure_boot_state()` Collector Returns Placeholder `UNKNOWN` | **Entire entry** (lines 87–95) describing the placeholder, its impact, and its tracking as a High-severity item. | **Outdated after M4** — the placeholder will be removed. The legacy collector's `_read_secure_boot_state()` will return a real value (or be replaced). | **REMOVE** this limitation entirely. |
| § Fixtures corpora are placeholders | `Every fixture file under … secureboot/ … is a zero-byte placeholder` | **Outdated if M6 fixture capture includes Secure Boot** — but not gated on M4. | **UPDATE** after M6, not M4. |

**Total changes needed:** 1 full section removed, 2 sections updated.

---

#### 22. `docs/HARDWARE_VALIDATION_MATRIX.md`

| Section | Current Wording | Outdated After M4? | Recommendation |
|---|---|---|---|
| E01 (VirtualBox) | `mokutil not found → caveats entry` | No — VirtualBox doesn't have `mokutil` | KEEP |
| E02 (Ubuntu 24.04, Secure Boot disabled) | `mokutil present and reports disabled` | No — still correct | KEEP |
| E03 (Ubuntu 24.04, Secure Boot enabled) | `mokutil --sb-state reports enabled` | No — still correct | KEEP |
| Notes | `bcs doctor Secure Boot check relies on the host mokutil binary. On VirtualBox (E01) it is absent → CommandNotFoundError, which is caught by the Host Discovery Orchestrator and reported as a caveat.` | No — still correct; M2b makes doctor use the HDO path, which surfaces caveats | KEEP |

No changes needed after M4 alone. M2b (doctor wiring) makes the orchestrator path the primary one for all environments.

---

#### 23. `docs/HARDWARE_MATRIX.md`

| Section | Current Wording | Outdated After M4? | Recommendation |
|---|---|---|---|
| Tool column | `mokutil (Ubuntu 24.04 package mokutil)` | No — tool unchanged | KEEP |
| Sources | `stdout of mokutil --sb-state` | No — unchanged | KEEP |
| VirtualBox row | `mokutil absent; adapter returns CommandNotFoundError` | No — still correct | KEEP |

No changes needed.

---

#### 24. `docs/IMPLEMENTATION_STATUS.md`

| Section | Current Wording | Outdated After M4? | Recommendation |
|---|---|---|---|
| §1 Overall — Partially implemented | `only 4 of its 8 named domain slots have a bound adapter, and no CLI command consumes it yet` | **Outdated** — still accurate for overall state, but needs nuance. After M2a + #70, `bcs inventory` does consume the HDO. After M4, the Secure Boot collector is no longer a placeholder. | **UPDATE** to reflect current state more accurately. |
| §2 Architecture Components — Secure Boot Adapter row | `Wired into the Host Discovery composition root (secure_boot slot). Not yet folded into HostInventory's own schema.` | No — "Not yet folded" remains true unless M2c changes it. | **UPDATE** status if M2c resolves the schema question. |
| §2 Architecture Components — Host Discovery Orchestrator row | `No bcs command passes runtime.host_discovery_orchestrator into collect_host_inventory() yet.` | **Outdated** — `bcs inventory` now passes it (issue #70). | **UPDATE** to reflect current state (inventory passes it, doctor does not). |
| §5 Host Discovery — Current limitations, bullet 2 | `HostDiscoverySnapshot's tool-adapter-sourced fields (firmwareBootConfiguration, secureBoot) are never folded into HostInventory's own schema` | No — remains true unless M2c passes | KEEP (or update if M2c resolves it) |
| §5 Host Discovery — Current limitations, bullet 1 | describes `bcs inventory` now consuming orchestrator and `bcs doctor` not yet | No — still accurate | KEEP |
| §8 Outstanding Work — Medium | None mention secure_boot directly. | No | KEEP |

**Total changes needed:** 2 sections updated (overall status, HDO row).

---

#### 25. `docs/LEGACY_COLLECTOR_DEPRECATION_PLAN.md`

| Section | Current Wording | Outdated After M4? | Recommendation |
|---|---|---|---|
| § Migration strategy — M2b + M4 | `memory, network, and (when wired) firmware/Secure Boot converge` | No — still the plan | KEEP |
| § Migration table — E1 | `collect_firmware() + _read_secure_boot_state() \| inventory/collectors.py \| Low — EFI + Secure Boot adapters are stable` | No — still correct; the dependency is stable | KEEP |

No changes needed.

---

#### 26. `docs/LEGACY_COLLECTOR_MIGRATION_AUDIT.md`

| Section | Current Wording | Outdated After M4? | Recommendation |
|---|---|---|---|
| §1.1 — `collect_firmware()` row | `Beta milestone: M2b (doctor wiring) + M4 (Secure Boot real implementation)` | No — still the plan | KEEP |
| §1.1 — `collect_firmware()` row | `Secure Boot always returns UNKNOWN (placeholder)` | **Outdated after M4** — it will return a real value. | **UPDATE** to "Secure Boot returns real value via adapter path (M4)." |
| §3 — snapshot field audit, `secure_boot` | `Dead output. Real data is produced (not UNKNOWN), nobody reads it.` | **Outdated after M4 + M2b** — doctor and inventory will read it. | **UPDATE** to "Consumed by doctor (M2b) and inventory via firmware path (M4)." |
| §6 — Technical Debt: Secure Boot adapter runs but output discarded | Wasted subprocess (`mokutil`) on every `bcs` invocation | **Outdated after M4** — output is consumed by firmware field. | **UPDATE** to resolve status or downgrade to LOW if only consumed via one path. |
| §6 — Technical Debt: `_read_secure_boot_state()` always returns UNKNOWN | Documented placeholder, real impl in adapter | **Outdated after M4** — the placeholder is replaced. | **REMOVE** or mark as resolved. |
| §7 — Collector Fate: `collect_firmware()` | **Delete** — Replaced by EFI + Secure Boot adapters; trigger: After Migration 2 | No — Migration 2 is firmware in service.py, which depends on M2b+M4 | KEEP |
| §8 — Sprint Plan, Sprint 4 cleanup | `Fix: Secure Boot adapter dead output (consumed via Migration 2)` | **Outdated after M4** — consumed. | **UPDATE** to "Done: Secure Boot adapter consumed via M2b + M4." |

**Total changes needed:** 5 sections updated after M4.

---

#### 27. `docs/HDO_MIGRATION_PLAN.md`

| Section | Current Wording | Outdated After M4? | Recommendation |
|---|---|---|---|
| § General (mentions `_read_secure_boot_state` as not migrated) | Implies `_read_secure_boot_state` is still a placeholder | **Outdated after M4** — the placeholder is gone. | **UPDATE** to reflect resolved status. |

**Total changes needed:** 1 section updated.

---

#### 28. `docs/ISSUE_70_IMPLEMENTATION_CHECKLIST.md`

(No direct Secure Boot mentions — issue #70 was storage focused.)

No changes needed.

---

#### 29. `docs/REAL_WORLD_VALIDATION.md`

(No direct Secure Boot mentions — this is a historical record of the first VM execution.)

No changes needed.

---

### A.4 `docs/decisions/` — ADRs

#### 30. `docs/decisions/0011-host-discovery-orchestrator.md`

| Section | Current Wording | Outdated After M4? | Recommendation |
|---|---|---|---|
| § Context | `this project anticipates several more Discovery domains (Secure Boot, Filesystem, Network, CPU, Memory, TPM)` | No — still correct (Secure Boot adapter exists) | KEEP |
| § Decision, point 3 | `Eight explicit, named, optional slots … EFI, Storage, Secure Boot, Filesystem, Network, CPU, Memory, TPM` | No — still correct | KEEP |
| § Consequences | `bcs.inventory.collectors.collect_cpu/collect_memory/collect_network need no signature change … Only tool-based adapters (efi, and later storage, secure_boot, filesystem, tpm) need explicit binding` | No — still correct. Secure Boot adapter is bound, as anticipated. | KEEP |

No changes needed.

---

#### 31. `docs/decisions/0010-efi-adapter-read-only-scope.md`

| Section | Current Wording | Outdated After M4? | Recommendation |
|---|---|---|---|
| § Context | `Host Inventory … can report whether a machine is UEFI-capable and its Secure Boot state` | No — still correct | KEEP |
| § Consequences | `bcs doctor/bcs inventory gain a path to real UEFI boot-entry visibility` | No — still aspirational; M4 doesn't change this | KEEP |

No changes needed.

---

#### 32. `docs/decisions/0009-platform-layer-command-runner.md`

| Section | Current Wording | Outdated After M4? | Recommendation |
|---|---|---|---|
| § Context | `bcs.inventory.collectors deliberately avoids external tools … with documented placeholder gaps (IP address enumeration, Secure Boot byte-value parsing)` | **Outdated after M4** — Secure Boot gap closed. IP gap closed by M3. | **UPDATE** to remove "Secure Boot byte-value parsing" from placeholder gaps list. |

**Total changes needed:** 1 section updated.

---

#### 33. `docs/decisions/0008-host-inventory-ports-and-adapters.md`

| Section | Current Wording | Outdated After M4? | Recommendation |
|---|---|---|---|
| § Amendment — Decision | `FirmwareInfo (which stays a firmware-only fact area: UEFI presence, Secure Boot state, firmware vendor/version)` | No — still correct | KEEP |

No changes needed.

---

#### 34. `docs/decisions/0005-yaml-as-unified-configuration-format.md`

| Section | Current Wording | Outdated After M4? | Recommendation |
|---|---|---|---|
| § Context | `Boot Manager needs configuration (menu entries, branding, Secure Boot posture)` | No — still correct | KEEP |

No changes needed.

---

### A.5 `docs/specifications/` and `docs/architecture/`

#### 35. `docs/specifications/platform-requirements.md`

| Section | Current Wording | Outdated After M4? | Recommendation |
|---|---|---|---|
| § PLAT-003 / PLAT-004 | `Secure Boot is a related but distinct concern: many UEFI machines ship with Secure Boot enabled by default` | No — requirement unchanged | KEEP |
| Compatibility Matrix | `Firmware \| UEFI (Secure Boot aware)` | No — still correct | KEEP |

No changes needed.

---

#### 36. `docs/architecture/boot-manager.md`

| Section | Current Wording | Outdated After M4? | Recommendation |
|---|---|---|---|
| § Firmware assumptions | `Boot Manager assumes UEFI firmware exclusively (PLAT-003). … Secure Boot (PLAT-004) … constrains what can be executed` | No — Boot Manager is Phase 1, not affected by M4 | KEEP |
| § Design decisions | `Secure Boot posture: ship a signed boot chain vs. document a supported "Secure Boot disabled" deployment mode (PLAT-004).` | No — still a Phase 1 decision | KEEP |

No changes needed.

---

### A.6 `docs/` — Guide, Glossary, Fixtures

#### 37. `docs/glossary.md`

| Section | Current Wording | Outdated After M4? | Recommendation |
|---|---|---|---|
| Secure Boot entry | `Secure Boot — a UEFI firmware feature … Platform-level constraint on Boot Manager's design (PLAT-004).` | No — still correct | KEEP |

No changes needed.

---

#### 38. `cli/tests/fixtures/secureboot/README.md`

(Zero-byte placeholder fixtures. The README describes the corpus naming convention and required scenarios.)

| Section | Current Wording | Outdated After M4? | Recommendation |
|---|---|---|---|
| Capture command | `LC_ALL=C LANG=C mokutil --sb-state > <fixture-name>.txt` | No — still the correct command | KEEP |
| Required scenarios | Lists `enabled`, `disabled`, `setup-mode`, `no-setup-mode-line`, `unavailable-stderr` | No — still the required set | KEEP |
| Fixture files | All zero-byte placeholders | **Outdated** — not gated on M4, but M4 + M6 should produce real captures. | **UPDATE** after real captures exist (M6), not M4. |

---

### A.7 Documents with No Secure Boot Mentions (verified)

No review needed for these documents:

- `docs/VM_DEMO_GUIDE.md` (UEFI mentions only, no Secure Boot)
- `docs/VM_CHECKLIST.md` (UEFI mentions only, no Secure Boot)
- `docs/VM_FIRST_BOOT.md` (UEFI + EFI mentions only, no Secure Boot)
- `docs/VM_INSTALLATION.md` (no Secure Boot)
- `docs/VM_VALIDATION.md` (UEFI mentions only)
- `docs/VM_BUG_REPORT_TEMPLATE.md` (no Secure Boot)
- `docs/VM_TEST_LOG.md` (no Secure Boot)
- `docs/MVP_DEMO_PLAN.md` (Secure Boot mentioned only in passing in an architecture slide — no change needed)
- `docs/STANDARDS.md` / `docs/standards/` files (no Secure Boot)
- `docs/processes/` (no Secure Boot)
- `docs/guides/` (no Secure Boot)
- `docs/FILESYSTEM_ADAPTER.md` (mentions Secure Boot only as comparative reference — no change needed)
- `docs/NETWORK_ADAPTER.md` (mentions Secure Boot only as comparative reference — no change needed)
- `docs/STORAGE_ADAPTER.md` (no Secure Boot)
- `docs/NETWORK_ADAPTER_IMPLEMENTATION_PLAN.md` (no Secure Boot)
- `docs/repository-organization.md` (no Secure Boot)

---

## B. Document Dependency Graph

```
SPECIFICATION.md (§1: PLAT-004) ──────────────────────────┐
  └── docs/specifications/platform-requirements.md          │
      (PLAT-003/PLAT-004 detail)                            │
                                                            │
ARCHITECTURE.md (§5: Secure Boot constraint)                │
                                                            │
docs/CONFIGURATION.md                                       │
  (§ spec.security.secureBoot.mode — desired policy)        │
                                                            │
docs/HOST_INVENTORY.md ────────────────────────┐            │
  (§ Open Questions: placeholder)              │            │
                                               ▼            ▼
                            ┌─────────────────────────────────────┐
                            │      BACKWARD-COMPATIBLE            │
                            │      INPUTS (KEEP)                  │
                            │  SPECIFICATION.md, ARCHITECTURE.md  │
                            │  CONFIGURATION.md, ADR-0008,        │
                            │  glossary.md, platform-requirements │
                            │  boot-manager.md                   │
                            └─────────┬───────────────────────────┘
                                      │
                                      ▼
              ┌───────────────────────────────────────────────┐
              │           DESIGN DOCUMENTS                    │
              │  SECURE_BOOT_ADAPTER.md (status banner,       │
              │    Purpose, Future Extensibility, Open Q's,   │
              │    Sequence Diagram)                          │
              │  HOST_DISCOVERY_ORCHESTRATOR.md               │
              │    (§ Relationship to Host Inventory)         │
              │  PLATFORM_LAYER.md                            │
              │    (§ abstract, Approved Design Decisions)    │
              │  ADR-0009                                     │
              │    (§ placeholder gaps)                       │
              └─────────┬─────────────────────────────────────┘
                        │
                        ▼
              ┌───────────────────────────────────────────────┐
              │         STATUS / ROADMAP DOCUMENTS            │
              │  BETA_ROADMAP.md (M4 status, objectives,      │
              │    collector plan, risks, effort)             │
              │  IMPLEMENTATION_STATUS.md                     │
              │    (§1, §2 HDO row, §5 limitations)           │
              │  KNOWN_LIMITATIONS.md                         │
              │    (§ secure_boot placeholder — REMOVE)       │
              │    (§ doctor not consuming — UPDATE)          │
              │    (§ schema not folded — UPDATE)             │
              │  BETA_PREPARATION_REPORT.md                   │
              │  LEGACY_COLLECTOR_MIGRATION_AUDIT.md          │
              │  LEGACY_COLLECTOR_DEPRECATION_PLAN.md         │
              │  HDO_MIGRATION_PLAN.md                        │
              │  EFI_ADAPTER.md                               │
              └─────────┬─────────────────────────────────────┘
                        │
                        ▼
              ┌───────────────────────────────────────────────┐
              │         VALIDATION / RELEASE DOCS             │
              │  BETA_VALIDATION_PLAN.md (KEEP)               │
              │  BETA_RELEASE_CHECKLIST.md (KEEP)             │
              │  HARDWARE_VALIDATION_MATRIX.md (KEEP)         │
              │  HARDWARE_MATRIX.md (KEEP)                    │
              │  VM_TEST_LOG.md (KEEP)                        │
              └───────────────────────────────────────────────┘
```

**Key insight:** The backward-compatible inputs (SPEC, ARCHITECTURE, CONFIG, ADR-0008,
glossary, platform-requirements, boot-manager) do not change when M4 lands. The
design documents and ADRs that mention placeholder gaps do need updating. The
status/roadmap documents need completion updates. The validation documents are
unaffected.

---

## C. Documentation Update Order

The updates must be applied in dependency order: no document should reference a
document that hasn't been updated yet.

```
Phase 1 — Pre-M4 (can be done any time before M4 merges)
  Can be done before M4 because they don't describe the implementation itself:

  1. PLATFORM_LAYER.md              → Remove "Secure Boot byte-value parsing"
     (2 sections: abstract + Approved Design Decisions)    from placeholder gaps

  2. ADR-0009                       → Same removal from context section
     (docs/decisions/0009-...)      about placeholder gaps

  Rationale: These documents describe the collector's current behaviour. They
  can be updated to say "the gap was closed" even before the code lands, as
  long as it's merged after the code. Or they can be updated atomically with
  the code change.

Phase 2 — With M4 Code Change (atomic, same PR as the implementation)
  These must be updated atomically with the code because they would be
  factually incorrect after the merge:

  3. KNOWN_LIMITATIONS.md           → REMOVE entire § `_read_secure_boot_state()`
     (1 section removed)            Returns Placeholder `UNKNOWN` entry

  4. HOST_INVENTORY.md              → UPDATE § Open Questions: "Resolved — the
     (1 section updated)            `_read_secure_boot_state()` placeholder has
                                    been replaced with a real implementation."

Phase 3 — Post-M4 (within same release cycle, may be separate PRs)
  These document the M4 outcome and depend on knowing what actually happened:

  5. BETA_ROADMAP.md                → Mark M4 items ✅, update exit criteria
     (5 sections updated)           from future-tense to past-tense, update
                                    risks section, update collector plan,
                                    update objectives

  6. IMPLEMENTATION_STATUS.md       → Update §1, §2 HDO row, §5 limitations
     (2-3 sections updated)         to reflect M4 completion

  7. BETA_PREPARATION_REPORT.md     → UPDATE key findings (placeholder resolved)
     (2 sections updated)           and documentation status

  8. LEGACY_COLLECTOR_MIGRATION_AUDIT.md
     (5 sections updated)           → UPDATE `collect_firmware()` row, snapshot
                                    field audit, tech debt register entries,
                                    sprint plan

  9. SECURE_BOOT_ADAPTER.md         → UPDATE status banner, § Purpose (both
     (6 sections updated)           paragraphs), § Future Extensibility,
                                    § Open Questions, § Sequence Diagram
                                    (doctor wiring)

  10. HDO_MIGRATION_PLAN.md         → UPDATE mention of `_read_secure_boot_state`
      (1 section updated)           as still a placeholder

Phase 4 — Dependent on M2b + M2c (may be different releases)
  These require M2b (doctor wiring) or M2c (ADR-0008 amendment) to be done:

  11. HOST_DISCOVERY_ORCHESTRATOR.md
      (1 section updated)           → UPDATE § Relationship to Host Inventory
                                    after M2c resolves the schema question

  12. KNOWN_LIMITATIONS.md (again)  → UPDATE § HDO not consumed by doctor
      (2 sections updated)          (after M2b) and § schema not folded
                                    (after M2c)
```

---

## D. Post-Implementation Review Checklist

After the M4 code change merges, verify each of the following items:

### Correctness checks

- [ ] `bcs inventory` reports `secureBoot: enabled` (or `disabled`, matching firmware state) — never `UNKNOWN`.
- [ ] `bcs doctor --check secure-boot` returns `OK` or `WARN` based on real state — never `UNKNOWN`.
- [ ] `bcs doctor --check secure-boot` on VirtualBox (no `mokutil`) reports a meaningful caveat via the orchestrator, not `UNKNOWN`.
- [ ] Legacy `bcs.inventory.collectors._read_secure_boot_state()` returns a real `SecureBootState` value (not `UNKNOWN`).
- [ ] No adapter is invoked twice per `bcs doctor` invocation (the duplicate `/sys/firmware/efi` read in `_check_firmware` + `_check_secure_boot` is resolved).

### Documentation checks

- [ ] `PLATFORM_LAYER.md` — "Secure Boot byte-value parsing" removed from placeholder gaps list in both the abstract and the Approved Design Decisions section.
- [ ] `ADR-0009` — same removal from § Context placeholder gaps.
- [ ] `KNOWN_LIMITATIONS.md` — § `_read_secure_boot_state()` Collector Returns Placeholder `UNKNOWN` entry removed.
- [ ] `HOST_INVENTORY.md` — § Open Questions updated to mark the Secure Boot gap as resolved.
- [ ] `BETA_ROADMAP.md` — M4 items marked `✅`, exit criteria affirmed, collector deprecation plan updated, risks section updated, actual effort recorded.
- [ ] `IMPLEMENTATION_STATUS.md` — overall status, Secure Boot Adapter row, and HDO limitation rows reflect current state.
- [ ] `BETA_PREPARATION_REPORT.md` — key findings and documentation status updated.
- [ ] `LEGACY_COLLECTOR_MIGRATION_AUDIT.md` — snapshot field audit, tech debt entries, and sprint plan updated.
- [ ] `SECURE_BOOT_ADAPTER.md` — status banner, Purpose, Future Extensibility, Open Questions, and Sequence Diagram updated.
- [ ] `HDO_MIGRATION_PLAN.md` — placeholder mention resolved.

### Release engineering checks

- [ ] `CHANGELOG.md` — M4 change entry added under `[Unreleased]`.
- [ ] `ruff check .` passes.
- [ ] `ruff format --check .` passes.
- [ ] `mypy` (strict mode) passes.
- [ ] `pytest` passes (all existing tests + new M4 tests).

### Hardware-environment-specific checks

- [ ] E02 (Ubuntu 24.04 physical, NVMe, UEFI, Secure Boot disabled): Secure Boot reported as `disabled`.
- [ ] E03 (Ubuntu 24.04 physical, NVMe, UEFI, Secure Boot enabled): Secure Boot reported as `enabled`.
- [ ] E06 (LliureX 23 physical, NVMe, UEFI): Secure Boot matches actual firmware state.
- [ ] E01 (VirtualBox, any disk controller): Secure Boot reported as caveat (`mokutil` absent), not `UNKNOWN`.
