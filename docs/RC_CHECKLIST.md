# Release Candidate Checklist — `bcs` CLI

**Date:** 2026-07-09
**Purpose:** What remains before this repository can be tagged as a Release Candidate, per `docs/BETA_ROADMAP.md`'s own pre-defined release ladder. This checklist is additive to — not a replacement for — `docs/BETA_RELEASE_CHECKLIST.md` (the 60+-item pre-release verification checklist) and `docs/BETA_ROADMAP.md` (the milestone tracker); it exists to answer specifically "what's between here and an RC tag," cross-referencing both rather than duplicating their content.

---

## Where This Repository Sits on Its Own Release Ladder

`docs/BETA_ROADMAP.md § Candidate Beta Release Criteria` already defines four named checkpoints:

| Checkpoint | Requires | Tag | Status today |
|---|---|---|---|
| Beta preview | M1 + M2a | `v0.2.0-beta.1` | ⚠️ M2a done (code); **M1 not done** (no E01 storage validation logged) |
| **Beta RC1** | M1 + M2a + M2b + M4 | `v0.2.0-rc.1` | ⚠️ M2a + M4 done (code); **M1 and M2b not done** |
| Beta RC2 | Above + M3 + M5 | `v0.2.0-rc.2` | ⚠️ M3 done (code); **M5 not started at all** |
| Beta final | Above + M6 + M7 | `v0.2.0` | ⚠️ M6 partial; **M7 not done** |

**This repository does not yet meet its own RC1 bar.** `pyproject.toml` still declares `version = "0.1.0"` — no version bump has happened at any checkpoint, including the earliest one (`v0.2.0-beta.1`). This is the single clearest, most objective release-readiness signal in the whole repository: whatever the various Beta/RC preparation documents say, the package itself has not been bumped even once.

---

## Remaining Beta Tasks

From `docs/BETA_ROADMAP.md`'s own Definition of Done for Beta (unchecked items only, cross-checked against current code):

| # | Task | Verified status |
|---|---|---|
| 1 | **M1: storage array non-empty on E01, 27 `VM_VALIDATION.md` cases pass.** | Not done — no VM test log entry post-M3/M4 confirms this on a real VirtualBox VM; only unit-test/Windows-dev-box verification exists in this session's own audits. |
| 2 | **M2b: `bcs doctor` surfaces `caveats`; `esp`/`usb-storage` gain an adapter-derived equivalent.** | Not done — confirmed via `docs/RC_TECHNICAL_DEBT_REPORT.md` findings #6, #7, #12: no business-logic service exists yet, `caveats` is collected but never shown to the user. |
| 3 | **M2c: ADR-0008 amendment for Discovery-domain schema folding — accepted or explicitly deferred.** | Not done — no such ADR amendment exists in `docs/decisions/`; not even explicitly deferred in writing anywhere this pass found. |
| 4 | **M5: physical validation on E02/E03/E06, logged in `VM_TEST_LOG.md`.** | Not started — see [Remaining Hardware Validation](#remaining-hardware-validation). |
| 5 | **No P0/P1 bugs open.** | Cannot be verified from this environment (no access to the project's issue tracker's live state); the one P0-adjacent defect found this session (the `--help` routing bug, `docs/BETA_READINESS_REPORT.md`) was fixed and closed within the same pass that found it. |
| 6 | **`KNOWN_LIMITATIONS.md` reflects current state, no stale entries.** | Not done — two stale/inaccurate entries identified in `docs/BETA_READINESS_REPORT.md` (FakeCommandRunner resolved) and `docs/RC_TECHNICAL_DEBT_REPORT.md` (FrozenModel description). |
| 7 | **`IMPLEMENTATION_STATUS.md` updated for every code change.** | Not verified in this pass — recommend a dedicated check before RC tagging. |
| 8 | **`CHANGELOG.md` has complete `[Unreleased]` entries for the Beta phase.** | Substantially populated (confirmed non-empty, actively maintained across this session's tasks and the concurrent session's work) but has never been *cut* into a versioned release section — see [Remaining Release Engineering](#remaining-release-engineering). |
| 9 | **A Beta release tag exists.** | **Does not exist.** No `v0.2.0*` tag anywhere in this repository's history as of this pass. |
| 10 | **`ruff`, `ruff format --check`, `mypy`, `pytest` all pass on the release commit.** | ✅ Confirmed passing as of this pass's own quality-gate run (see [Quality Gates](#quality-gates-verified-this-pass)) — the one item on this list that's unconditionally done. |
| 11 | **CI is green on the release commit.** | Presumed true (gates above pass locally, matching what CI runs) but not independently confirmed against an actual CI run in this pass — recommend confirming the `all-green` job on the exact commit intended for tagging. |

---

## Remaining Hardware Validation

Per `docs/HARDWARE_VALIDATION_MATRIX.md` and `docs/BETA_ROADMAP.md` M5 — **entirely unstarted.** Every "M3/M4 complete" checkmark elsewhere in this repository's documentation is explicitly qualified "(code)" only; not one environment in the matrix has a logged validation run since the Host Discovery Orchestrator, Storage, Network, or Secure Boot integrations landed. This is the single largest release blocker and cannot be resolved from this (or any) AI coding session — it requires physical machines or configured VMs and a human (or automation with real device access) to run `docs/BETA_RELEASE_CHECKLIST.md`/`scripts/validate-beta.sh` against them and log results in `docs/VM_TEST_LOG.md`.

Minimum bar before RC2 (per the roadmap's own criteria): E02, E03, E06 (physical Ubuntu 24.04 NVMe/UEFI, and LliureX 23 — the actual target platform) all validated and logged.

---

## Remaining Documentation

| Item | Source | Fix effort |
|---|---|---|
| ADR-0011's own "Consequences" text says HDO consumption is "not yet implemented" — false since issue #70/M3 | `docs/RC_TECHNICAL_DEBT_REPORT.md` finding #16 / Architecture Verification A9 | Trivial — one paragraph, in an Accepted ADR (editing an Accepted ADR's implementation-status prose is not the same as reopening its Decision; see AGENTS.md's own "an accepted ADR is normative for the decision it records" — the Decision doesn't change, only the stale status note). |
| `docs/CLI.md` line 98: ADR-0009 marked "(Accepted, not yet implemented)" — Platform Layer is fully implemented | `docs/BETA_READINESS_REPORT.md` | Trivial — one phrase. |
| `KNOWN_LIMITATIONS.md`: `FakeCommandRunner` entry stale (now resolved) | `docs/BETA_READINESS_REPORT.md` | Trivial — remove or mark resolved. |
| `KNOWN_LIMITATIONS.md`: `FrozenModel`/`FrozenExtensibleModel` entry mischaracterizes `bcs.config.models` | `docs/RC_TECHNICAL_DEBT_REPORT.md` Corrections | Trivial — reword. |
| `collectors.py` module docstring calls all ten collectors "placeholders" (four are permanent) | `docs/RC_TECHNICAL_DEBT_REPORT.md` finding #13 | Trivial — one paragraph. |
| `collect_network()` docstring still frames IP enumeration as an open gap (closed since M3) | `docs/RC_TECHNICAL_DEBT_REPORT.md` finding #14 | Trivial — one paragraph. |
| `docs/CLI.md`'s documented `bcs help build`/`bcs build help` forms are not implemented at all | `docs/BETA_READINESS_REPORT.md` | Either implement (a real feature — out of scope for a feature freeze) or narrow the doc to match reality (trivial). Recommend the latter for RC; revisit the former post-RC if wanted. |
| `docs/BETA_READINESS_REPORT.md` and `docs/BETA_READINESS_AUDIT.md` — two same-day, similarly-named, differently-scoped reports (CLI/packaging vs. docs/tooling) | Both exist in `docs/` as of this pass | Needs a maintainer decision: cross-link them, merge them, or rename one — not resolved by this pass since it was produced by a concurrent session mid-flight (see `docs/BETA_READINESS_REPORT.md`'s own closing note). |
| `docs/COLLECTOR_CALL_GRAPH.md`'s "unreachable on healthy systems" claim overstated for storage/network fallbacks | `docs/RC_TECHNICAL_DEBT_REPORT.md` Corrections | Trivial — split the claim in two, cpu/memory vs. storage/network. |

None of these block RC on complexity — all are small, low-risk wording fixes. They collectively block RC on *volume and correctness*: an RC branded "release candidate" should not ship with ADRs and known-limitations docs that describe an earlier implementation state than what's actually in the code.

---

## Remaining Release Engineering

| Item | Status |
|---|---|
| Version bump (`pyproject.toml` `0.1.0` → `0.2.0-beta.1` or directly to an RC-appropriate version, per the roadmap's ladder) | **Not done.** |
| `CHANGELOG.md` `[Unreleased]` cut into a versioned section | **Not done.** |
| Git tag | **Not done** — no `v0.2.0*` tag exists. |
| GitHub Release notes | **Not done** — no release published. |
| `docs/BETA_RELEASE_CHECKLIST.md`'s 60+ items run end-to-end on the release commit | Not verified in this pass — that checklist includes physical-hardware items this pass cannot execute; the CLI-only/packaging subset was independently re-verified in `docs/BETA_READINESS_REPORT.md` (wheel/sdist/editable installs, all 5 commands, all 3 output modes). |

---

## Required GitHub Actions

Current `.github/workflows/ci.yml` (verified this pass, unchanged since `docs/BETA_READINESS_REPORT.md`'s review): 4 jobs (`lint`, `typecheck`, `test` on 3.12/3.13, `cli-smoke-test`) gated behind `all-green`. Gaps carried forward from that report, still open:

- No smoke-test step exercises a subcommand's own `--help` (the exact gap that let the `--help` routing bug ship undetected — now fixed in code, but CI still can't catch a *future* regression of the same shape).
- No smoke-test step exercises `--output yaml`.
- No smoke-test step exercises a non-zero exit path.
- Stub commands are never smoke-tested.

**Before tagging RC**, recommend either closing these gaps or explicitly accepting the risk in writing (a one-line note in `docs/BETA_RELEASE_CHECKLIST.md` or this document) — CI/tooling changes are, per this session's own working agreement, the concurrent session's area, so this pass documents rather than implements them (consistent with "touch production code only if you discover a genuine defect" — a CI coverage gap is a process gap, not a code defect).

No new GitHub Actions workflows are needed beyond closing these gaps — the existing 4-job structure already covers lint/type/test/smoke; an RC doesn't need a fifth job, just a more thorough fourth one.

---

## Version Bump, Tag Creation, Release Process

Recommended sequence, following `docs/BETA_ROADMAP.md`'s own ladder (not a new process — restating it here so it's checkable in one place alongside this pass's other findings):

1. Resolve M1 (E01 storage validation) and M2b (caveats + esp/usb-storage migration, or an explicit written decision to defer them past RC1 — see `docs/RC_LEGACY_EXIT_PLAN.md` step 1-2).
2. Bump `pyproject.toml` `version` to `0.2.0-beta.1`; tag; this is the earliest checkpoint the roadmap defines, and this repository hasn't reached it yet despite M2a/M3/M4 all being code-complete.
3. Once M2c is either accepted or explicitly deferred in writing, and M2b is done: bump to `0.2.0-rc.1`, tag.
4. Once M5 (physical hardware validation, E02/E03/E06 minimum) is logged in `VM_TEST_LOG.md`: bump to `0.2.0-rc.2`, tag.
5. Once M6 (infrastructure/QoL — `FakeCommandRunner` is already done; real fixture captures and the CI smoke-test gaps above remain) and M7 (documentation reconciliation, complete `CHANGELOG.md`, this release process itself) are done: bump to `0.2.0`, tag, publish the GitHub Release.

Each tag should be created only after re-running this pass's quality gates (`ruff`, `ruff format --check`, `mypy --strict`, `pytest`) on the exact commit being tagged, per `docs/BETA_READINESS_REPORT.md`'s own closing recommendation.

---

## Definition of Done (for an RC tag specifically)

Distinct from — and stricter than — `docs/BETA_ROADMAP.md`'s general Beta Definition of Done, scoped to what "Release Candidate" should mean for this repository:

- [ ] M1 and M2b complete (RC1's own stated bar).
- [ ] `pyproject.toml` version bumped to match the tag being created.
- [ ] `CHANGELOG.md` `[Unreleased]` cut into the versioned section for this release.
- [ ] All items in [Remaining Documentation](#remaining-documentation) resolved (all are trivial-effort; no reason to carry stale ADR/limitation text into an RC).
- [ ] `docs/RC_TECHNICAL_DEBT_REPORT.md`'s 4 **REMOVE BEFORE RC** items resolved (this is the literal contract that classification implies).
- [ ] `docs/RC_TECHNICAL_DEBT_REPORT.md`'s **DISCUSS** items each have an explicit maintainer decision recorded (even if the decision is "defer past RC" — the point is no item is silently forgotten).
- [ ] `ruff check`, `ruff format --check`, `mypy --strict`, `pytest` all green on the exact release commit.
- [ ] CI `all-green` job confirmed green on the exact release commit (not just presumed from local gates).
- [ ] Git tag created following the version scheme in [Version Bump, Tag Creation, Release Process](#version-bump-tag-creation-release-process).
- [ ] The two same-day "Beta Readiness" docs (`docs/BETA_READINESS_REPORT.md`, `docs/BETA_READINESS_AUDIT.md`) reconciled — cross-linked at minimum, merged if a maintainer prefers.

**M2c, M5, and M6's remaining items are explicitly NOT required for RC1** per the roadmap's own ladder — only for RC2/final. Do not block RC1 on them.

---

## Quality Gates (verified this pass)

Re-run on the current `main` HEAD as part of producing this checklist, no code changes required to pass:

| Gate | Result |
|---|---|
| `ruff check` | ✅ All checks passed |
| `ruff format --check` | ✅ All files formatted |
| `mypy` (strict) | ✅ No issues found |
| `pytest` | ✅ All tests passed |

(Exact counts reproduced in this pass's final report to the user, not repeated here to avoid a second source of truth that could drift from the actual run.)
