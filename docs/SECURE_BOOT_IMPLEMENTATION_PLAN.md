# Secure Boot Implementation Plan — Beta Milestone M4

> **Status: Analysis and planning only — nothing in this document has been implemented.** This is the pre-implementation investigation, technical analysis, and implementation plan for Beta Milestone M4 (`docs/BETA_ROADMAP.md`), prepared so coding can begin immediately in a follow-up session. No Python files were changed to produce this document; it was written by reading the existing Secure Boot Adapter, the legacy collector, `bcs doctor`, `bcs inventory`, `docs/SECURE_BOOT_ADAPTER.md`, `docs/HOST_INVENTORY.md`, and ADR-0011.

## Executive Summary

**Secure Boot detection is already fully implemented, tested (100% coverage), and wired into the Host Discovery Orchestrator's composition root.** `bcs inventory` reports `secureBoot: unknown` and `bcs doctor --check secure-boot` prints "a placeholder in this phase" for exactly the same reason `bcs inventory` used to report `storage: []` before issue #70, and always-empty `ip_addresses` before Beta M3: **nothing consumes the adapter's output.** This is a wiring gap, not a detection-mechanism gap — `mokutil` remains the correct mechanism, already implemented per an `Accepted` design document.

Two independent consumers need wiring, and they require two *different* fixes, not one:

1. **`bcs inventory`** — reuses the exact `orchestrator → translate-or-fallback` pattern issue #70/M3 established. Small, low-risk, mirrors precedent exactly.
2. **`bcs doctor --check secure-boot`** — cannot reuse that same pattern as-is. `bcs doctor` deliberately never calls `HostDiscoveryOrchestrator.discover()` at all (ADR-0011 explicitly rejected that design — see [§4](#4-adr-verification)); each check reads one adapter directly. Fixing `bcs inventory` alone does **not** fix `bcs doctor`'s placeholder message, since `_check_secure_boot()` calls `collect_firmware()` directly, never `collect_host_inventory()`.

Both are small (the doctor fix is one function's ~15 line body plus a signature change), both are provided for completeness, and both are recommended — but they are separable, and the plan flags the boundary explicitly, since the user's own instruction did not name `bcs doctor` and it is unwise to assume its inclusion silently. See [§ 6 Open Decision for the User](#6-open-decision-for-the-user).

---

## 1. Investigation: Current Implementation

### 1.1 The Platform Layer Secure Boot Adapter — fully implemented, not the problem

`cli/src/bcs/platform/adapters/secureboot/` is complete and accepted (`docs/SECURE_BOOT_ADAPTER.md`, status `Accepted; fully implemented`):

- `models.py` — `SecureBootState` (`ENABLED`/`DISABLED`/`UNSUPPORTED`/`UNKNOWN`, independently defined from `bcs.inventory.models.SecureBootState`, same four values) and `SecureBootStatus` (`state`, `setup_mode: bool | None`, `raw_text: str`).
- `parser.py` — `parse_secure_boot_status(text: str) -> SecureBootStatus`, a pure function parsing `mokutil --sb-state` line-by-line output.
- `errors.py` — `SecureBootError(PlatformError)`, `SecureBootUnavailableError`, `SecureBootParseError`.
- `adapter.py` — `read_secure_boot_status(runner: CommandRunner, *, timeout_seconds=5.0) -> SecureBootStatus`, the only module that calls `mokutil`.

All four modules are at 100% statement/branch coverage (`cli/tests/test_platform_adapters_secureboot_*.py`). **Already wired** into the Host Discovery composition root: `bcs.app.main()` binds `secure_boot=functools.partial(read_secure_boot_status, runner=command_runner)` (`cli/src/bcs/app.py:217`), and `HostDiscoveryAdapters.secure_boot`/`HostDiscoverySnapshot.secure_boot` are concretely typed `Callable[[], SecureBootStatus] | None`/`SecureBootStatus | None`. Calling `runtime.host_discovery_orchestrator.discover().secure_boot` today already returns a correct, real `SecureBootStatus` on any machine with `mokutil` installed — this has been true since the Secure Boot Adapter's own wiring commit, well before this plan.

**Nothing needs to change here.** The gap is entirely downstream.

### 1.2 The legacy collector — the visible `UNKNOWN` placeholder

`cli/src/bcs/inventory/collectors.py:79-92`:

```python
def collect_firmware() -> FirmwareInfo:
    """Probe UEFI/Secure Boot state - see PLAT-003, PLAT-004."""
    if not _SYS_FIRMWARE_EFI.is_dir():
        return FirmwareInfo(uefi=False, secure_boot=SecureBootState.UNSUPPORTED)
    return FirmwareInfo(uefi=True, secure_boot=_read_secure_boot_state())


def _read_secure_boot_state() -> SecureBootState:
    if not _SYS_FIRMWARE_EFIVARS.is_dir():
        return SecureBootState.UNKNOWN
    # Parsing the SecureBoot-<GUID> EFI variable's actual byte value is a
    # placeholder for future work; presence of efivars only confirms the
    # firmware exposes UEFI variables at all, not the Secure Boot toggle.
    return SecureBootState.UNKNOWN
```

This function only ever returns two values: `UNSUPPORTED` (BIOS/legacy boot — `/sys/firmware/efi` absent) or `UNKNOWN` (every UEFI system, regardless of actual Secure Boot state) — it never returns `ENABLED`/`DISABLED`. The docstring has said "placeholder for future work" since the function's original commit; this is a documented, not-a-regression gap (the same category as `collect_storage()`'s NVMe-only glob before issue #70).

### 1.3 Why `secure-boot` always reports `UNKNOWN` — two independent consumers, neither wired

**`bcs inventory`** — `bcs.inventory.service.collect_host_inventory()` calls `firmware=collectors.collect_firmware()` **unconditionally**, outside the `if orchestrator is None` / `else` branch entirely (`cli/src/bcs/inventory/service.py:172`). Unlike `cpu`/`memory`/`storage`/`network`, `firmware` is not in the orchestrator-conditional list at all — `snapshot.secure_boot` is never read by this function, even when an orchestrator is supplied. This is architecturally identical to the pre-M3 state of `network`: the orchestrator has correct data, but the aggregation function never asks for it.

**`bcs doctor --check secure-boot`** — `cli/src/bcs/commands/doctor.py:57-70`, `_check_secure_boot()` calls `collect_firmware()` **directly**, with no `runtime`/orchestrator involvement at all:

```python
def _check_secure_boot() -> CheckResult:
    firmware = collect_firmware()
    state = firmware.secure_boot
    ...
```

`_ALL_CHECKS["secure-boot"] = lambda _runtime: _check_secure_boot()` — the `runtime` parameter is received and discarded. This is deliberate design, not an oversight: `docs/HOST_INVENTORY.md` documents that `bcs doctor` calls collectors directly (not `collect_host_inventory()`) so a failing/slow collector for one check can never block or crash an unrelated one — see [§4](#4-adr-verification) for why this also forecloses "just call `collect_host_inventory(orchestrator)` from doctor" as a fix.

**Conclusion:** `mokutil` is, and remains, the correct mechanism — it is already implemented, tested, and accepted. Neither consumer's gap is a detection problem; both are wiring gaps, and they require two separate wiring fixes because they use two structurally different data paths today.

---

## 2. Technical Analysis

### 2.1 Current execution flow

**`bcs inventory` (today):**
```
run_inventory(runtime)
  -> collect_host_inventory(orchestrator=runtime.host_discovery_orchestrator)
       -> firmware = collectors.collect_firmware()      # UNCONDITIONAL, ignores orchestrator
            -> _read_secure_boot_state()                 # always UNKNOWN or UNSUPPORTED
       -> [snapshot.secure_boot is computed via orchestrator.discover() as a side
           effect of computing cpu/memory/storage/network, but its value is
           never read into `firmware`]
```

**`bcs doctor --check secure-boot` (today):**
```
run_doctor(runtime, checks=["secure-boot"])
  -> _ALL_CHECKS["secure-boot"](runtime)          # lambda discards `runtime`
       -> _check_secure_boot()                     # no orchestrator, no CommandRunner
            -> collect_firmware() -> _read_secure_boot_state() -> UNKNOWN
```

Neither path ever calls `read_secure_boot_status()` (the adapter) or reads `HostDiscoverySnapshot.secure_boot`, despite both being fully populated and correct whenever `runtime.host_discovery_orchestrator`/`runtime.command_runner` are available (i.e. always, in every real `bcs` invocation — the composition root builds them unconditionally).

### 2.2 Available Linux mechanisms

| Mechanism | Status in this codebase | Assessment |
|---|---|---|
| **`mokutil --sb-state`** (wrap, parse text) | **Chosen and fully implemented** (`docs/SECURE_BOOT_ADAPTER.md`, `Accepted`). | Recommended path — already built, tested, wired to the orchestrator. Requires the `mokutil` package (present on Ubuntu/LliureX by default alongside `shim-signed`; not guaranteed on every base image). |
| **Direct `efivarfs` byte read** of `/sys/firmware/efi/efivars/SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c` | **Explicitly considered and not chosen**, per `docs/SECURE_BOOT_ADAPTER.md § Future Extensibility`: *"This document chose the tool-wrapping route for consistency with the EFI and Storage adapters' own shape... not because the `efivarfs`-direct alternative was found lacking."* Also the literal mechanism `_read_secure_boot_state()`'s own docstring names as its own "placeholder for future work." | **Not recommended for this milestone.** Reimplementing it now would (a) contradict the already-`Accepted` design document's own stated choice without a new design decision, and (b) duplicate ~15 lines of binary-parsing logic (4-byte little-endian attribute header + 1-byte boolean) that provides no benefit over the adapter already sitting unused. Recorded here only because the investigation was asked to consider it explicitly. |
| **`libefivar` / `python-efivar` bindings** | Not evaluated for this milestone. | New third-party dependency; `SECURE_BOOT_ADAPTER.md` names it only as a hypothetical "different backend" possibility (`§ Future Extensibility`), never proposed. Out of scope. |

**Recommendation: use `mokutil` via the existing, accepted adapter — wire it in, do not reimplement.**

### 2.3 Permissions required

- `/sys/firmware/efi` presence: reading a directory's existence — no special permission (`_SYS_FIRMWARE_EFI.is_dir()`, already used).
- `mokutil --sb-state` reads the `SecureBoot` UEFI variable via `efivarfs`. In practice, `SecureBoot`'s efivarfs file is readable by unprivileged users on stock Ubuntu/LliureX (confirmed by `mokutil`'s own widely-documented no-sudo-required behavior for state queries — only MOK *enrollment*/*deletion* subcommands need root). No `sudo`/root requirement is expected for this specific fix.
- If a hardened system *does* restrict read access, `mokutil` exits non-zero with a recognizable "permission denied" `stderr`, which `_UNAVAILABLE_PATTERNS` in `secureboot/adapter.py` already maps to `SecureBootUnavailableError` — already handled by the existing adapter, requires no new code.

### 2.4 Expected behaviour

| Scenario | `HostDiscoverySnapshot.secure_boot` (already correct today) | `bcs inventory` (after this plan) | `bcs doctor --check secure-boot` (after this plan, if included — see §6) |
|---|---|---|---|
| **Secure Boot enabled** | `SecureBootStatus(state=ENABLED, ...)` | `secureBoot: enabled` | `[ OK ] secure-boot Secure Boot is enabled` |
| **Secure Boot disabled** | `SecureBootStatus(state=DISABLED, ...)` | `secureBoot: disabled` | `[ WARN ] secure-boot Secure Boot is disabled` |
| **Unsupported firmware (BIOS/legacy boot)** | `None` (adapter raises `SecureBootUnavailableError`, isolated into a `caveats` entry — mokutil itself reports "not supported on this system") | Falls back to `collect_firmware()`, which already independently detects BIOS mode via `_SYS_FIRMWARE_EFI.is_dir()` and returns `UNSUPPORTED` correctly today | `[ SKIP ] secure-boot not applicable: not running under UEFI` (unchanged from today) |
| **`mokutil` missing (`CommandNotFoundError`)** | `None` (isolated into `caveats`) | Falls back to `collect_firmware()` → `UNKNOWN` (same placeholder as today, but only on this one machine, not universally) | `[ WARN ] secure-boot Secure Boot state could not be determined (mokutil not found)` — degrades gracefully, never crashes `bcs doctor` |
| **BIOS mode** (no `/sys/firmware/efi` at all) | `None` (`mokutil` itself would report "EFI variables are not supported on this system") | `collect_firmware()`'s own existing top-level check already short-circuits to `UNSUPPORTED` before `_read_secure_boot_state()` is ever called — unaffected by this plan either way | `[ SKIP ]` — unaffected, unchanged |

The fallback-to-`UNKNOWN` case (mokutil missing) is **not a regression** — it is exactly today's behaviour, now scoped to only the specific machines lacking `mokutil`, rather than universal.

---

## 3. Implementation Plan

### 3.1 Files to modify

| File | Change | Est. LOC |
|---|---|---|
| `cli/src/bcs/inventory/service.py` | Add `_translate_secure_boot_state()` (maps `platform.secureboot.models.SecureBootState` → `inventory.models.SecureBootState`, both 4-value `StrEnum`s with identical string values — a trivial value-preserving conversion, no filtering, unlike storage's `device_type` filter). Wire `firmware` into the orchestrator branch: compute `collect_firmware()` as today, then when `snapshot.secure_boot is not None`, override only `secure_boot` via `firmware.model_copy(update={...})` — `uefi`/`vendor`/`version` remain collector-sourced always, since the adapter has no opinion on them. Update module docstring (mirrors storage/network's own 5a/5b paragraphs from Beta M3). | ~30-40 |
| `cli/src/bcs/commands/doctor.py` | *(Only if the doctor-side fix is included — see §6.)* Change `_check_secure_boot()` → `_check_secure_boot(runtime: RuntimeContext) -> CheckResult`; call `read_secure_boot_status(runtime.command_runner)` directly (not via `orchestrator.discover()` — see §4's ADR-0011 citation for why); catch `PlatformError` and degrade to a `warn`/`skip` `CheckResult` with a descriptive message, mirroring the graceful-degradation style already used by other checks. Update `_ALL_CHECKS["secure-boot"]` from `lambda _runtime: _check_secure_boot()` to the bare `_check_secure_boot` reference (matching `_check_config`'s existing style). Add the `read_secure_boot_status` import. | ~25-35 |
| `cli/tests/test_inventory_service.py` | New tests: `_translate_secure_boot_state()` unit tests (4 states); orchestrator-supplies-secure-boot (adapter path); orchestrator-secure-boot-unset-falls-back (fallback path); orchestrator-secure-boot-platform-error-falls-back (isolated `PlatformError` path); extend `test_orchestrator_is_called_exactly_once` with a `secure_boot_adapter` counting-adapter assertion; adjust `test_orchestrator_other_sections_unaffected`'s docstring/scope (firmware's `uefi`/vendor/version are unaffected, `secure_boot` is not — same pattern as storage/network's own exclusion). | ~90-120 |
| `cli/tests/test_commands_doctor.py` | *(Only if doctor-side fix included.)* **Breaks an existing test**, not just extends one: `test_check_secure_boot_maps_every_state` currently calls `doctor_module._check_secure_boot()` with **zero arguments** — this raises `TypeError` the moment the signature gains `runtime`, the exact same failure shape as issue #70's `patched_inventory` fixture bug. Must be rewritten to accept `make_runtime_context` and monkeypatch `doctor_module.read_secure_boot_status` (not `collect_firmware`) returning a canned `SecureBootStatus` per parametrized state. New tests: `SecureBootUnavailableError` → `warn`/`skip`; `SecureBootParseError` → `warn`; `CommandNotFoundError` → `warn` (mokutil missing); confirm `runtime.command_runner` is the instance passed to `read_secure_boot_status` (not a second, independently constructed one). | ~50-70 |
| `docs/HOST_DISCOVERY_ORCHESTRATOR.md` | Update § Relationship to Host Inventory (add a 5c paragraph for `firmware`/`secure_boot`, mirroring 5a/5b's shape) and the status banner. | ~15-25 |
| `docs/IMPLEMENTATION_STATUS.md` | §5 Host Discovery Status "Current limitations" (drop `secureBoot` from the "never folded into `HostInventory`'s own schema" list — see §4), §8 Outstanding Work if applicable, Host Inventory row in §2. | ~10-15 |
| `docs/HOST_INVENTORY.md` | § Open Questions / Explicitly Deferred: remove or resolve the "Secure Boot byte-value parsing" bullet (it currently frames the *old*, not-chosen `efivarfs`-direct approach as the anticipated fix — needs correcting to describe what was actually implemented). | ~5-10 |
| `docs/KNOWN_LIMITATIONS.md` | Remove/resolve the `_read_secure_boot_state()` Collector Returns Placeholder `UNKNOWN` entry (or narrow it, mirroring how the Network Adapter entry was narrowed/folded in Beta M3, depending on whether the doctor-side fix ships in the same change). | ~10-20 |
| `docs/SECURE_BOOT_ADAPTER.md` | § Future Extensibility (the "closing `HostInventory`'s placeholder" bullet currently reads as unresolved/gated on the ADR-0008 amendment — needs correcting per §4's finding) and § Open Questions ("whether/how this adapter is wired into `bcs doctor`" — resolve if doctor-side ships). | ~10-15 |
| `CHANGELOG.md` | New `[Unreleased]` entry, mirroring the M3 entry's level of detail. | ~15-25 |

**Total estimated LOC: ~260-380** (inventory-only fix: ~150-210; add doctor fix: +~110-170).

### 3.2 Tests required

Already itemized per-file above. Summary by category, mirroring the M3 checklist's own structure:

- **Translation unit tests** — `_translate_secure_boot_state()` for all 4 `SecureBootState` values (including `UNSUPPORTED`, which the parser never actually produces today but the translation function should still handle correctly for completeness/future-proofing).
- **Adapter path** — orchestrator wired, `snapshot.secure_boot` populated → `bcs inventory` reports the real state.
- **Fallback path** — `secure_boot` slot unset → falls back to `collect_firmware()`'s existing placeholder, unchanged.
- **Isolated `PlatformError`** — adapter raises (e.g. `mokutil` not found) → falls back identically to the unset-slot case, `caveats` still records it at the snapshot level.
- **No orchestrator** — `collect_host_inventory()` called with no orchestrator at all → byte-for-byte identical to pre-M4 behaviour (regression guard).
- *(If doctor-side included)* **Doctor state mapping** — `ENABLED`/`DISABLED`/`UNSUPPORTED`/`UNKNOWN` → `ok`/`warn`/`skip`, now sourced from a mocked `read_secure_boot_status` instead of a mocked `collect_firmware`.
- *(If doctor-side included)* **Doctor error degradation** — every `PlatformError` subclass the adapter can raise degrades to a non-crashing `CheckResult`, never propagates and never crashes `bcs doctor`.

### 3.3 Compatibility risks

| Risk | Assessment |
|---|---|
| **Silent behaviour change for `bcs inventory --output json` consumers** | `firmware.secureBoot` may now report `enabled`/`disabled` where it previously always reported `unknown`. This is the intended fix, not a regression, but — mirroring issue #70's own flagged risk for `storage[*].model`/`.size_bytes` — worth calling out explicitly in `CHANGELOG.md` since it is a real content change for any script currently branching on `secureBoot == "unknown"`. |
| **`_check_secure_boot()` signature change** (if doctor-side included) | Breaking for any code calling it directly (none exists outside its own test file, per a repo-wide check before implementation) — a private (`_`-prefixed) function, not a public API. Low risk. |
| **`mokutil` absence on non-standard images** | Already handled by the existing adapter (`CommandNotFoundError` → isolated fallback for `bcs inventory`; would need explicit catch in `bcs doctor` if that fix is included). No new risk introduced by this plan; the fallback is exactly today's `UNKNOWN` behaviour, scoped narrower. |
| **Reading efivarfs on non-Linux dev machines (Windows, macOS)** | Adapter already raises `CommandNotFoundError` (`mokutil` not on `PATH`) — falls back cleanly, matching how `storage`/`network` already degrade gracefully on this project's own Windows dev environment (confirmed during M3: `bcs inventory` exits 0 with empty/fallback data on Windows). No new risk. |
| **`FirmwareInfo.model_copy(update=...)` on a frozen Pydantic model** | Standard, safe Pydantic pattern — `model_copy` always returns a new instance regardless of `frozen=True`; no risk. |

### 3.4 Fallback strategy

Identical in shape to storage/network's own established fallback (issue #70 / Beta M3), extended to a scalar field rather than a list:

```python
firmware = collectors.collect_firmware()
if orchestrator is not None and snapshot.secure_boot is not None:
    firmware = firmware.model_copy(
        update={"secure_boot": _translate_secure_boot_state(snapshot.secure_boot)}
    )
```

- **Orchestrator not given at all** → `collect_firmware()` unchanged, byte-for-byte identical to today.
- **`secure_boot` slot unset** (no adapter wired — a build without `mokutil` support compiled in, hypothetically) → `snapshot.secure_boot is None` → `firmware` unchanged, falls back to the collector's `UNKNOWN`/`UNSUPPORTED`.
- **Adapter raises `PlatformError`** (isolated inside the orchestrator into `caveats`, `snapshot.secure_boot` is `None`) → same fallback as the unset case — no crash, no exception surfaces to the caller.
- **Adapter succeeds** → `secure_boot` overridden with the real, translated state; `uefi`/`vendor`/`version` remain whatever `collect_firmware()` already determined (the adapter has no opinion on those).

No new fallback mechanism is introduced — this reuses the exact pattern already proven twice.

---

## 4. ADR Verification

**No new ADR is required, and no existing ADR needs amendment.**

1. **The Secure Boot Adapter itself already concluded no ADR is needed** (`docs/SECURE_BOOT_ADAPTER.md § ADR Recommendation`): every mechanism it uses (Platform Layer `CommandRunner`, read-only/domain-driven adapter shape, composition-root wiring) was already decided by ADR-0008/0009/0010/0011. Nothing in this plan touches the adapter itself.

2. **Translating `secure_boot` into the *existing* `HostInventory.firmware.secure_boot` field is not a schema change**, and therefore not gated on the still-open ADR-0008 amendment ([ADR-0011](decisions/0011-host-discovery-orchestrator.md) Decision point 6 — "does not itself add new fields to `HostInventory`"). That amendment governs *adding new top-level fields* (`firmwareBootConfiguration`, `storageTopology`, etc. as new JSON keys) — it does not govern sourcing an *already-existing* field's value from richer Discovery-domain data with a collector fallback. Decision point 7 already covers exactly that: `collect_host_inventory()`'s `orchestrator` parameter, with per-field snapshot-or-fallback logic. This is the identical reasoning issue #70's own checklist used for `storage`, and Beta M3 used for `network` — both already-accepted, already-shipped precedent for this exact category of change.

   **This is a documentation staleness finding, not an open question**: `docs/SECURE_BOOT_ADAPTER.md § Future Extensibility` (the "Closing `HostInventory`'s `FirmwareInfo.secure_boot` placeholder" bullet) and § Open Questions currently read as if this translation is gated on the ADR-0008 amendment — but that text predates the M2/M3 precedent that settled the question. `docs/IMPLEMENTATION_STATUS.md`'s "never folded into `HostInventory`'s own schema" list (§5) still names `secureBoot` alongside genuinely-unresolved items (`firmwareBootConfiguration`) — the same kind of staleness `storage`/`network` were removed from during their own wiring. Both are listed in [§5](#5-documentation-impact) below.

3. **`bcs doctor` must not call `HostDiscoveryOrchestrator.discover()`** — this is an explicit, already-recorded rejection, not a new design question: [ADR-0011](decisions/0011-host-discovery-orchestrator.md) § Alternatives Considered states plainly: *"Let `bcs doctor` also depend on the full `HostDiscoveryOrchestrator.discover()` sweep, for consistency with `bcs inventory`. Rejected: `doctor`'s existing, deliberate asymmetry... would be lost if a single `--check` had to pay for... an unrelated domain's adapter call. `doctor` instead reads one named slot off `HostDiscoveryAdapters` directly, preserving that asymmetry."* This directly shapes §3.1's recommendation: `_check_secure_boot(runtime)` must call `read_secure_boot_status(runtime.command_runner)` directly — **not** `runtime.host_discovery_orchestrator.discover().secure_boot`, which would pay for `efi`/`storage`/`filesystem`/`network`/`cpu`/`memory` just to answer one question, exactly what this ADR rejected. `RuntimeContext.command_runner` already exists and is exactly the seam this alternative anticipated.

No credible alternative mechanism is being chosen here (mokutil was already chosen), no component boundary changes, and no platform scope changes — none of `docs/decisions/README.md § When to Write an ADR`'s four triggers apply.

---

## 5. Documentation Impact

**Only identifying which documents will require updates — none have been modified.**

| Document | What needs updating (when implemented) |
|---|---|
| `docs/HOST_DISCOVERY_ORCHESTRATOR.md` | Status banner; § Relationship to Host Inventory (new paragraph for `firmware`/`secure_boot`, mirroring 5a/5b's shape from M3). |
| `docs/IMPLEMENTATION_STATUS.md` | §2 Architecture Components (Host Inventory row); §5 Host Discovery Status "Current limitations" (drop `secureBoot` from the not-folded-into-schema list — see §4 finding 2); §8 Outstanding Work if the "Secure Boot" item there still references the old placeholder framing. |
| `docs/HOST_INVENTORY.md` | § Open Questions / Explicitly Deferred — the "Secure Boot byte-value parsing" bullet needs correcting (it currently describes the *not-chosen* efivarfs-direct approach as the anticipated fix). |
| `docs/KNOWN_LIMITATIONS.md` | The `_read_secure_boot_state()` Collector Returns Placeholder `UNKNOWN` entry — resolve fully if the doctor-side fix ships in the same change, or narrow it to `bcs doctor`-only (mirroring the Network Adapter entry's own narrowing pattern from M3) if `bcs inventory`-only ships first. |
| `docs/SECURE_BOOT_ADAPTER.md` | § Future Extensibility (the "closing `HostInventory`'s placeholder" bullet — correct per §4 finding 2); § Open Questions ("whether/how this adapter is wired into `bcs doctor`" — resolve if doctor-side ships); status banner's "Not yet done" list. |
| `docs/BETA_ROADMAP.md` | Mark M4's own checklist items/exit-criteria complete as each is satisfied; note if the doctor-side item is deferred separately from the inventory-side item. |
| `CHANGELOG.md` | New `[Unreleased]` entry. |

**Not touched** (verified, no update needed): `docs/CLI.md`, `ARCHITECTURE.md`, `SPECIFICATION.md`, `docs/CONFIGURATION.md`, any ADR file (per §4), `docs/PATTERNS.md`, `docs/decisions/README.md`.

---

## 6. Open Decision for the User

The user's request named "M4 (real Secure Boot detection)" and "the remaining visible placeholder during a real demo," without explicitly naming `bcs doctor`. A real demo would show **both** placeholders (`bcs inventory`'s `secureBoot: unknown` and `bcs doctor`'s "a placeholder in this phase" warning) — but per `docs/BETA_ROADMAP.md`, the doctor-side fix is structurally part of a separate, larger milestone (M2b), and `_check_secure_boot()`'s signature change is a small but real, independent piece of work with its own test breakage to fix (§3.1). Recommend confirming scope before implementation begins:

- **Option A — `bcs inventory` only.** Smaller, self-contained, exactly mirrors the M2/M3 precedent shape. `bcs doctor --check secure-boot` continues showing its placeholder message until M2b.
- **Option B — `bcs inventory` + the minimal `bcs doctor` secure-boot fix** (not the rest of M2b's scope — no `network`/`caveats` changes to doctor). Fully resolves the demo-visible gap in both commands; slightly larger, touches one more file and breaks one more existing test.

This plan supports either option; §3.1's file list marks the doctor-side rows accordingly.

---

## Related Documents

- [docs/BETA_ROADMAP.md](BETA_ROADMAP.md) — Milestone M4's own goal/exit-criteria/dependency (M2b) statement.
- [docs/SECURE_BOOT_ADAPTER.md](SECURE_BOOT_ADAPTER.md) — the accepted adapter design this plan wires in, unmodified.
- [docs/HOST_DISCOVERY_ORCHESTRATOR.md](HOST_DISCOVERY_ORCHESTRATOR.md) — the orchestrator/composition-root pattern this plan reuses.
- [docs/ISSUE_70_IMPLEMENTATION_CHECKLIST.md](ISSUE_70_IMPLEMENTATION_CHECKLIST.md) — the storage precedent this plan's `bcs inventory` fix mirrors structurally.
- [docs/decisions/0011-host-discovery-orchestrator.md](decisions/0011-host-discovery-orchestrator.md) — Decision points 6/7 and the doctor-asymmetry Alternative Considered, both load-bearing for §4's conclusions.
- [docs/KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md) — the placeholder entry this plan will resolve.
