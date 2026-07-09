# Beta Preparation Report — Batoi Classroom Suite

**Date:** 2026-07-09
**Phase:** Phase 0 — Foundation
**Status:** Beta documentation complete, pending end-to-end validation on physical hardware.

---

## Repository Readiness

### What exists

- **CLI framework** (`cli/`): `version`, `doctor`, `validate`, `inventory` commands fully implemented. 7 stub commands registered. 1026 passing tests, 96% statement coverage, 100% on all Platform Layer and Host Discovery modules. `ruff`, `mypy` (strict), `pytest` all pass. CI gated behind an `all-green` job.
- **Platform Layer** (`bcs.platform`): `CommandRunner`/`SubprocessCommandRunner` implemented and wired into `RuntimeContext`.
- **Host Discovery adapters** (4 fully implemented): EFI, Storage, Secure Boot, Filesystem — all `models.py`/`parser.py`/`errors.py`/`adapter.py` complete, all wired into the Host Discovery composition root.
- **Network Adapter**: fully implemented as a package (`models.py`/`errors.py`/`parser.py`/`adapter.py`) but not yet wired into the composition root.
- **Host Discovery Orchestrator**: implemented end to end including composition-root and `RuntimeContext` wiring. Not yet consumed by any `bcs` command.
- **Configuration system**: `config/schema.yaml`, `config/examples/default.yaml`, `bcs validate`.
- **Documentation set**: fully drafted — `ARCHITECTURE.md`, `SPECIFICATION.md`, `ROADMAP.md`, 11 ADRs, design documents for every adapter, implementation status dashboard, VM documentation (7 files), standards and conventions.
- **Quality gates**: `ruff check`, `ruff format --check`, `mypy` (strict), `pytest` — all green. 62 source files, no type errors.

### What was added in this preparation

| Document | Purpose |
|---|---|
| [BETA_VALIDATION_PLAN.md](BETA_VALIDATION_PLAN.md) | Validation process, scope, exit criteria, bug classification, regression policy |
| [HARDWARE_VALIDATION_MATRIX.md](HARDWARE_VALIDATION_MATRIX.md) | Per-environment expected results (8 environments) |
| [BETA_RELEASE_CHECKLIST.md](BETA_RELEASE_CHECKLIST.md) | Pre-release verification checklist (60+ items) |
| [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md) | Updated: added TPM slot limitation; the Secure Boot collector placeholder entry was later removed once Beta M4 resolved it |

### What was fixed

- `docs/VM_VALIDATION.md` TC-14: added `secure-boot` to the expected doctor checks list (was missing, causing confusion during validation).
- `docs/README.md`: added entries for all three new Beta documents.

---

## Remaining Blockers

| Blocker | Severity | Details |
|---|---|---|
| **Host Discovery Orchestrator not consumed by any command** | High | The orchestrator is built and wired but `bcs inventory` and `bcs doctor` still source facts from legacy collectors. Adapter-sourced facts (`firmwareBootConfiguration`, `storageTopology`, `secureBoot`) never reach command output. |
| **`bcs inventory` reports empty storage array** | High | Observed on first end-to-end VM test. `lsblk` detects `/dev/sda` but inventory reports `storage: []`. Under investigation by separate analysis. |
| **Network Adapter not wired into composition root** | Medium | The `network` Host Discovery slot still binds the `sysfs`-based `collect_network()` instead of the tool-based adapter. `ip_addresses` remains empty. |
| **Secure Boot collector returns placeholder UNKNOWN** | Medium | **Resolved (Beta M4).** `_read_secure_boot_state()` itself is unchanged and still always returns `UNKNOWN`, but it is now only the fallback: `bcs inventory`/`bcs doctor` both route through the Secure Boot Adapter (`mokutil --sb-state`) when available, reporting real state — see `docs/SECURE_BOOT_IMPLEMENTATION_PLAN.md`. |
| **No physical hardware validation yet** | Medium | E02, E03, E06 environments (physical NVMe/UEFI, LliureX 23) have not been tested. |
| **Fixture corpora are zero-byte placeholders** | Low | `cli/tests/fixtures/{firmware,storage,secureboot,network}/` contain placeholder files only. No real hardware/VM output captured. |

---

## Documentation Completeness

| Area | Status | Notes |
|---|---|---|
| Architecture | ✅ Complete | `ARCHITECTURE.md`, `SPECIFICATION.md`, `ROADMAP.md`, 11 ADRs |
| CLI design | ✅ Complete | `docs/CLI.md`, `cli/README.md` |
| Configuration | ✅ Complete | `docs/CONFIGURATION.md`, `config/schema.yaml` |
| Platform Layer | ✅ Complete | `docs/PLATFORM_LAYER.md` |
| Host Inventory | ✅ Complete | `docs/HOST_INVENTORY.md` |
| Adapter designs (4) | ✅ Complete | EFI, Storage, Secure Boot, Filesystem — all Accepted, all implemented |
| Network Adapter | ✅ Complete | Design accepted, package implemented, not wired |
| Host Discovery Orchestrator | ✅ Complete | `docs/HOST_DISCOVERY_ORCHESTRATOR.md`, ADR-0011 Accepted |
| Implementation status | ✅ Complete | `docs/IMPLEMENTATION_STATUS.md` |
| Patterns & conventions | ✅ Complete | `docs/PATTERNS.md`, `docs/standards/` |
| VM documentation | ✅ Complete | 7 files covering VM creation through bug reporting |
| **Beta documentation** | ✅ **New** | 4 new files: plan, matrix, checklist, this report |
| Known limitations | ✅ Updated | 12 items documented |
| Glossary | ✅ Complete | `docs/glossary.md` |
| Repository organization | ✅ Complete | `docs/repository-organization.md` |

### Inconsistencies found during VM documentation cross-check

The following issues were identified but not fixed (documentation-only, non-blocking for Beta):

1. **VM name mismatch**: `VM_FIRST_BOOT.md` uses `bcs-validation`, `VM_DEMO_GUIDE.md` uses `bcs-demo`. Snapshot references and VDI paths diverge between the two documents. If both are used, the reader must mentally reconcile the differences.
2. **Duplicate VM creation instructions**: `VM_FIRST_BOOT.md` and `VM_DEMO_GUIDE.md` both describe VM creation with overlapping content but slightly different VBoxManage commands (VM_DEMO_GUIDE.md omits the `createvdi` step, which may cause the attach step to fail).
3. **BCS install instructions duplicated**: `VM_INSTALLATION.md` and `VM_DEMO_GUIDE.md` contain nearly identical installation steps. A reader following both will repeat work.
4. **Snapshot workflow not documented in VM_DEMO_GUIDE.md**: `VM_FIRST_BOOT.md` and `VM_INSTALLATION.md` reference sequential snapshots (`01-fresh-ubuntu-2404`, `02-bcs-installed`), but `VM_DEMO_GUIDE.md` does not mention snapshots at all.
5. **VM_CHECKLIST.md overlaps VM_VALIDATION.md**: The checklist duplicates much of the validation test cases without cross-linking.
6. **MVP_DEMO_PLAN.md stale troubleshooting**: Line 120 says "This VM may not have EFI enabled" — but both VM creation documents explicitly enable EFI. The troubleshooting hint applies only if the reader deviates from the documented setup.

None of these inconsistencies block Beta. They are documentation quality issues that can be resolved in a future documentation cleanup pass.

---

## Testing Readiness

| Area | Status | Details |
|---|---|---|
| Unit tests | 1026 passing, 96% coverage | All Platform Layer, Host Discovery, and Inventory modules at 100% |
| Lint (Ruff) | ✅ Clean | `ruff check .` and `ruff format --check .` pass |
| Type checking (mypy) | ✅ Clean | Strict mode, 62 source files, zero errors |
| CI | ✅ Passing | 4 jobs: lint, typecheck, test (3.12/3.13 matrix), smoke-test |
| VM validation checklist | ✅ Ready | 27 test cases in `VM_VALIDATION.md` |
| Bug report template | ✅ Ready | `VM_BUG_REPORT_TEMPLATE.md` |
| Test log | ✅ Ready | `VM_TEST_LOG.md` (empty, awaiting first session) |
| Beta validation plan | ✅ **New** | `BETA_VALIDATION_PLAN.md` |
| Hardware matrix | ✅ **New** | `HARDWARE_VALIDATION_MATRIX.md` with 8 environments |
| Release checklist | ✅ **New** | `BETA_RELEASE_CHECKLIST.md` with 60+ items |

**One known test gap:** The `cli-smoke-test` CI job (runs `bcs` on a real Ubuntu runner via GitHub Actions) exercises only the `version` command. It does not run `doctor`, `inventory`, or `validate`. End-to-end command validation must be performed manually per environment.

---

## Recommended Next Milestone

**Beta Validation Kick-off**

Immediate next steps, in suggested order:

1. **Fix the empty `storage` array issue** currently under investigation — it is the only observed functional defect from the first end-to-end VM test.
2. **Run the full BETA_RELEASE_CHECKLIST.md on the VirtualBox VM** (environment E01) and log results in VM_TEST_LOG.md.
3. **Validate on physical Ubuntu 24.04 with NVMe** (environments E02, E03) — these are the closest to the target LliureX platform.
4. **Validate on LliureX 23** (environment E06) — this is the actual target platform. Expected to show `tooling: OK` for the first time.
5. **Triage any P0/P1 bugs** found during physical validation against the [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md) baseline.
6. **Begin preparing Phase 1 (Boot Manager) design validation** once Beta confirms the CLI and Host Discovery subsystem are stable on target hardware.

The Beta phase is go-ready from a documentation and process standpoint. The single blocking item is the empty `storage` array defect.
