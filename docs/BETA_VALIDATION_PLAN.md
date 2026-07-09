# Beta Validation Plan — Batoi Classroom Suite (BCS)

## Purpose

Define the structured validation process for Batoi Classroom Suite's Phase 0 `bcs` CLI before inviting external testers. This plan ensures the CLI is installable, observable, and reliable across target environments before Beta begins.

## Scope

**In scope:**

- The `bcs` CLI framework: `--help`, `version`, `validate`, `inventory`, `doctor`
- Editable (`pip install -e ".[dev]"`) and regular (`pip install .`) installation paths
- All three output formats: text, JSON, YAML
- All nine doctor checks: `firmware`, `secure-boot`, `esp`, `storage`, `usb-storage`, `network`, `tooling`, `permissions`, `config`
- All Host Inventory sections: identity, firmware, operating system, CPU, memory, storage, network, EFI system partition, USB storage, tooling
- Stub commands: `build`, `install`, `deploy`, `backup`, `restore`, `update`, `config`
- Performance: command completion under 5 seconds
- Error handling: unknown commands, missing files, missing config
- Cross-environment validation: VirtualBox, physical hardware, Secure Boot on/off, storage backends

**Out of scope:**

- Boot Manager, Builder, and Deploy (Phases 1–3, not yet implemented)
- The Platform Layer adapter test suite (test-level coverage, already gated by CI)
- The Host Discovery Orchestrator consumption path (not yet wired into any command)
- Real-network PXE/multicast testing (PLAT-007 is a requirement, but the deploy command is a stub)
- Performance profiling beyond the 5-second wall-clock cutoff

## Goals

1. **Installability.** Every supported environment can install `bcs` from source without unexpected failures.
2. **Correctness.** Every implemented command produces the documented output structure. No crashes, no hangs, no corrupt output.
3. **Observability.** Every failure mode produces a clear, actionable message. Exit codes follow the published scheme.
4. **Determinism.** Repeated invocation on the same machine produces consistent results. No hidden state leaks between invocations.
5. **Environment coverage.** At least four distinct host configurations pass the validation checklist (see [HARDWARE_VALIDATION_MATRIX.md](HARDWARE_VALIDATION_MATRIX.md)).

## Exit Criteria

Beta validation is complete when all of the following hold:

- [ ] All 27 test cases in [VM_VALIDATION.md](VM_VALIDATION.md) pass on at least one Ubuntu 24.04 VirtualBox EFI/NVMe VM.
- [ ] `bcs validate ../config/examples/default.yaml` exits 0 on every supported environment.
- [ ] `bcs doctor` completes without crash on every supported environment (individual check results may vary by environment — see [HARDWARE_VALIDATION_MATRIX.md](HARDWARE_VALIDATION_MATRIX.md)).
- [ ] `bcs inventory --output json` produces parseable, schema-versioned JSON on every supported environment.
- [ ] No P0 or P1 bugs remain open.
- [ ] All P2 bugs have a documented workaround or are accepted as known limitations.
- [ ] The [BETA_RELEASE_CHECKLIST.md](BETA_RELEASE_CHECKLIST.md) is fully checked off for at least one environment.
- [ ] A test log entry exists in [VM_TEST_LOG.md](VM_TEST_LOG.md) documenting the validation session.

## Supported Environments

| ID | Environment | Storage | Firmware | Secure Boot | Priority |
|---|---|---|---|---|---|
| E01 | Ubuntu 24.04 (VirtualBox 7.x) | NVMe (virtual) | UEFI | N/A (VirtualBox does not implement SB) | Required |
| E02 | Ubuntu 24.04 (physical) | NVMe | UEFI | Disabled | Required |
| E03 | Ubuntu 24.04 (physical) | NVMe | UEFI | Enabled | Required |
| E04 | Ubuntu 24.04 (physical) | SATA SSD | UEFI | Either | Best-effort |
| E05 | Debian 12 (physical or VM) | NVMe or SATA | UEFI | Either | Informational |
| E06 | LliureX 23 (physical) | NVMe | UEFI | Either | Required |
| E07 | Ubuntu 24.04 (physical, USB SSD boot) | USB SSD | UEFI | Either | Informational |
| E08 | Ubuntu 24.04 (physical, USB flash) | USB flash | UEFI | Either | Informational |

See [HARDWARE_VALIDATION_MATRIX.md](HARDWARE_VALIDATION_MATRIX.md) for per-environment expectations.

## Validation Workflow

Each validation session follows this sequence:

1. **Prepare environment.** Set up the host per [VM_FIRST_BOOT.md](VM_FIRST_BOOT.md) (for VMs) or the equivalent physical-machine provisioning steps.
2. **Install BCS.** Follow [VM_INSTALLATION.md](VM_INSTALLATION.md) (commands are distribution-agnostic for Debian-based systems).
3. **Run checklist.** Execute every test case in [VM_VALIDATION.md](VM_VALIDATION.md) in order. Record each result.
4. **Report bugs.** Use [VM_BUG_REPORT_TEMPLATE.md](VM_BUG_REPORT_TEMPLATE.md) for any failure.
5. **Log session.** Append a session record to [VM_TEST_LOG.md](VM_TEST_LOG.md).
6. **Snapshot (VMs only).** Create a VirtualBox snapshot after a successful validation pass.

## Acceptance Criteria

| Area | Criterion |
|---|---|
| CLI startup | `bcs --help`, `bcs version`, `bcs` (bare) produce help text with exit code 0. |
| Validation | `bcs validate <valid-config>` exits 0. `bcs validate <missing-file>` exits non-zero with error message. |
| Inventory | `bcs inventory` prints 10 sections in text mode. `--output json` produces valid, schema-versioned JSON. `--output yaml` produces valid, parseable YAML. |
| Doctor | `bcs doctor` runs all checks and produces per-check status without crashing. Individual checks may warn or fail by environment. |
| JSON output | Every `--output json` variant is parseable by `python3 -m json.tool` and contains `schemaVersion`. |
| Error handling | Unknown command exits 8 with "unknown command" message. Stub commands print "not implemented in this phase" and exit non-zero. |
| Performance | `bcs doctor` and `bcs inventory` each complete in under 5 seconds (`time bcs doctor` real < 5s). |
| Reproducibility | Running `bcs doctor; bcs inventory; bcs validate` in sequence succeeds without cross-contamination. |

## Bug Classification

| Priority | Label | Definition | Response |
|---|---|---|---|
| P0 — Critical | `bug-p0` | CLI crashes, hangs, or produces incorrect data for any implemented command | Blocking — must be fixed before Beta can continue |
| P1 — High | `bug-p1` | A core command (`doctor`, `inventory`, `validate`) fails on a required environment | Must be fixed or explicitly accepted as a known limitation before Beta ends |
| P2 — Medium | `bug-p2` | Secondary feature affected (output format, stubs, edge case) | Must have documented workaround or be accepted as known limitation |
| P3 — Low | `bug-p3` | Cosmetic issue, typo, minor improvement | Tracked but non-blocking |

| Type | Label | Description |
|---|---|---|
| Bug (regression) | `regression` | Previously passing test case now fails |
| Bug (never worked) | `bug` | Functionality never worked as designed |
| Documentation | `documentation` | Error in documentation (spec, design docs, validation docs) |
| Validation gap | `test-gap` | Test case missing or incorrectly specified |
| Environment | `environment` | Issue caused by VM/hardware configuration, not BCS code |

## Regression Policy

- **Before Beta:** The validation baseline is zero. Every new environment is a fresh discovery.
- **During Beta:** A passing test case that later fails is a regression. Report with label `regression` and P1 priority.
- **After fixes:** The entire [VM_VALIDATION.md](VM_VALIDATION.md) checklist must be re-run on at least one environment before the fix is merged.
- **Snapshot workflow (VMs):** Roll back to the last known-good snapshot, apply the fix, re-validate. This guarantees the regression is in the code, not in environment drift.
- **Documentation regressions:** A change that makes a documented expectation false (e.g. changing an exit code without updating `CLI.md`) is a documentation regression, classified P2.
