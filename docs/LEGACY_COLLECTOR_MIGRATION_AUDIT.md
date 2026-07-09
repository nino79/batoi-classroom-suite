# Legacy Collector Migration Audit

**State as of the Legacy Collector Dependency Audit (Beta M6).**

Issue #70 has landed: `bcs inventory` now passes the Host Discovery Orchestrator and
sources `storage` from the Storage Adapter with a fallback to the legacy collector.
Beta M3 wired the Network Adapter in the composition root. This audit was performed
to classify every legacy collector by migration status and mark Category B (fallback
only) collectors with explicit ``.. deprecated::`` RST comments.

This document audits every remaining legacy collector, every `HostDiscoverySnapshot`
field, and every code path that still bypasses the orchestrator, then produces a
migration roadmap for the Beta phase.

---

## 1. Collector Function Audit

### 1.1 `collect_firmware()` — lines 79–83

| Attribute | Value |
|---|---|
| **Purpose** | Probe UEFI presence via `/sys/firmware/efi` directory existence; Secure Boot always returns `UNKNOWN` (placeholder) |
| **Adapter equivalent** | ✅ **EFI adapter** (`read_firmware_boot_configuration`) produces `FirmwareBootConfiguration` with `current_boot_number`, `boot_order`, `boot_entries`, `timeout_seconds`, `raw_text` |
| **Adapter wired?** | ✅ Yes — `app.py:214` via `functools.partial(read_firmware_boot_configuration, runner=command_runner)` |
| **HDO slot** | `HostDiscoverySnapshot.firmware_boot_configuration` |
| **Current callers** | `service.py:139` (always), `doctor.py:51,58` (always) |
| **Used by CLI?** | `bcs inventory` — via `_print_identity_and_firmware()` reading `HostInventory.firmware.uefi` and `.secure_boot` |
| **Fallback available?** | Not designed |
| **Fate** | **Migrate.** EFI adapter already produces richer data; only a mapping function is missing. |
| **Beta milestone** | M2b (doctor wiring) + M4 (Secure Boot real implementation) |

### 1.2 `collect_storage()` — lines 95–119

| Attribute | Value |
|---|---|
| **Purpose** | Glob `/dev/nvme[0-9]n[0-9]` — only matches NVMe; misses SATA/SCSI |
| **Adapter equivalent** | ✅ **Storage adapter** (`read_storage_topology`) produces `StorageConfiguration` with all `BlockDevice` entries |
| **Adapter wired?** | ✅ Yes |
| **HDO slot** | `HostDiscoverySnapshot.storage_topology` |
| **Current callers** | `service.py:124,133` (fallback only), `doctor.py:74` (always) |
| **Used by CLI?** | `bcs inventory` — via HDO path after #70 ✅ |
| **Fallback available?** | ✅ Yes — implemented in #70 (`service.py:130-134`) |
| **Fate** | **Deprecated (Category B).** Called only as fallback from `service.py` and unconditionally from `doctor.py`. Marked with ``.. deprecated::`` RST comment in source. Can be removed after doctor migrates. |
| **Beta milestone** | M1 (done), M2b (doctor) |

### 1.3 `collect_efi_system_partition()` — lines 105–128

| Attribute | Value |
|---|---|
| **Purpose** | Parse `/proc/mounts` for `/boot/efi`; derive device, UUID, filesystem, size, free space |
| **Adapter equivalent** | ⚠️ **No dedicated adapter.** But Storage adapter's `BlockDevice.partitions` already has all data: mount point, filesystem type, partition UUID, GPT PARTTYPE GUID. ESP is identified by PARTTYPE `c12a7328-f81f-11d2-ba4b-00a0c93ec93b`. |
| **Adapter wired?** | N/A (no adapter) |
| **HDO slot** | None |
| **Current callers** | `service.py:143` (always), `doctor.py:82` (always) |
| **Used by CLI?** | `bcs inventory` — via `_print_efi_system_partition()` |
| **Fallback available?** | Not designed |
| **Fate** | **Migrate.** New business-logic service (not a full adapter) that scans `snapshot.storage_topology.devices[].partitions` for the ESP GUID. |
| **Beta milestone** | New (post-M2b) |

### 1.4 `collect_usb_storage()` — lines 189–205

| Attribute | Value |
|---|---|
| **Purpose** | Enumerate removable USB block devices via sysfs heuristics (removable attribute + `usb` in resolved sysfs path) |
| **Adapter equivalent** | ⚠️ **No dedicated adapter.** But Storage adapter's `BlockDevice.is_removable` identifies removable devices. USB-specific check (`usb` in sysfs path) may or may not be needed — the legacy collector does a cross-check the storage adapter does not. |
| **Adapter wired?** | N/A (no adapter) |
| **HDO slot** | None |
| **Current callers** | `service.py:145` (always), `doctor.py:91` (always) |
| **Used by CLI?** | `bcs inventory` — via `_print_usb_storage()` |
| **Fallback available?** | Not designed |
| **Fate** | **Migrate.** Filter `snapshot.storage_topology.devices` by `is_removable` and resolve USB-vs-eMMC ambiguity (same problem the legacy collector already has). |
| **Beta milestone** | New (post-M2b) |

### 1.5 `collect_identity()` — lines 275–283

| Attribute | Value |
|---|---|
| **Purpose** | Read primary MAC from `sys/class/net` + DMI product UUID from `/sys/class/dmi/id/product_uuid` |
| **Adapter equivalent** | ⚠️ **No dedicated adapter.** But: (1) DMI UUID could come from EFI adapter's `FirmwareBootConfiguration.smbios` field (if present — verify the EFI adapter model); (2) primary MAC comes from network adapter output. |
| **Adapter wired?** | N/A (no adapter) |
| **HDO slot** | None |
| **Current callers** | `service.py:138` (always) |
| **Used by CLI?** | `bcs inventory` — via `_print_identity_and_firmware()` |
| **Fallback available?** | Not designed |
| **Fate** | **Deprecate.** Both data points exist in other adapters; no new adapter needed. |
| **Beta milestone** | New (post-M2b) |

### 1.6 `collect_operating_system()` — lines 298–306

| Attribute | Value |
|---|---|
| **Purpose** | Read `/etc/os-release` pretty name + `platform.uname()` for arch/kernel |
| **Adapter equivalent** | ❌ **None planned.** Pure stdlib reads, no subprocess. |
| **Adapter wired?** | N/A |
| **HDO slot** | None (not part of `HostDiscoveryAdapters` — would need a new slot) |
| **Current callers** | `service.py:140` (always) |
| **Used by CLI?** | `bcs inventory` — via `_print_os_cpu_memory()` |
| **Fallback available?** | N/A |
| **Fate** | **Keep.** Reuse as HDO adapter callable (same pattern as `collect_cpu`/`collect_memory`). Add a new `HostDiscoveryAdapters.operating_system` slot. |
| **Beta milestone** | New (infrastructure) |

### 1.7 `collect_cpu()` — lines 340–346

| Attribute | Value |
|---|---|
| **Purpose** | Read `/proc/cpuinfo` model name + `os.cpu_count()` + `platform.machine()` |
| **Adapter equivalent** | ❌ **None planned.** Pure stdlib reads, no subprocess. |
| **Adapter wired?** | N/A — reused directly as HDO slot callable (`app.py:219`) |
| **HDO slot** | `HostDiscoverySnapshot.cpu` |
| **Current callers** | `service.py:121,127` (fallback), HDO slot |
| **Used by CLI?** | ✅ Yes — via HDO snapshot in `bcs inventory` |
| **Fallback available?** | ✅ Yes — `service.py:127` |
| **Fate** | **Keep.** Already reused by HDO. Never create a tool-based adapter. |
| **Beta milestone** | N/A (already done) |

### 1.8 `collect_memory()` — lines 319–330

| Attribute | Value |
|---|---|
| **Purpose** | Read `/proc/meminfo` MemTotal/MemAvailable in bytes |
| **Adapter equivalent** | ❌ **None planned.** Pure stdlib reads, no subprocess. |
| **Adapter wired?** | N/A — reused directly as HDO slot callable (`app.py:220`) |
| **HDO slot** | `HostDiscoverySnapshot.memory` |
| **Current callers** | `service.py:122,128` (fallback), HDO slot |
| **Used by CLI?** | ✅ Yes — via HDO snapshot in `bcs inventory` |
| **Fallback available?** | ✅ Yes — `service.py:128` |
| **Fate** | **Keep.** Already reused by HDO. Never create a tool-based adapter. |
| **Beta milestone** | N/A (already done) |

### 1.9 `collect_network()` — lines 258–291

| Attribute | Value |
|---|---|
| **Purpose** | Read `/sys/class/net/*/address` + `operstate`; `ip_addresses` always `[]` (placeholder) |
| **Adapter equivalent** | ✅ **Network adapter** (`read_network_interfaces`) — fully implemented, 100% tested, produces `NetworkInterfaceStatus` with real IP addresses |
| **Adapter wired?** | ✅ **Yes (Beta M3).** `app.py` now binds the Network Adapter via the composition root. `collect_network` is only a fallback when the adapter slot is unset or fails. |
| **HDO slot** | `HostDiscoverySnapshot.network` |
| **Current callers** | `service.py:123,129` (HDO path, fallback only), `doctor.py:99` (legacy) |
| **Used by CLI?** | ✅ Yes — real IP addresses now appear in `bcs inventory` output |
| **Fallback available?** | ✅ Yes — `collect_network` is called when the adapter slot is unset or fails |
| **Fate** | **Deprecated (Category B).** Marked with ``.. deprecated::`` RST comment in source. Replace with Network Adapter in the composition root. |
| **Beta milestone** | M3 (done) |

### 1.10 `collect_tooling()` — lines 360–365

| Attribute | Value |
|---|---|
| **Purpose** | `shutil.which()` for Clonezilla and Partclone |
| **Adapter equivalent** | ❌ **None planned.** Pure `shutil.which`, no subprocess, no hardware. |
| **Adapter wired?** | N/A |
| **HDO slot** | None (not part of `HostDiscoveryAdapters`) |
| **Current callers** | `service.py:147` (always), `doctor.py:117` (always) |
| **Used by CLI?** | `bcs inventory` — via `_print_tooling()` |
| **Fallback available?** | N/A |
| **Fate** | **Keep.** Add as a new HDO adapter slot (same pattern as `collect_cpu`/`collect_memory`). |
| **Beta milestone** | New (infrastructure) |

---

## 2. `collect_host_inventory()` — Field-by-Field Audit

Source code: `service.py:112-148`

| HostInventory Field | Line | Source with Orchestrator | Source without Orchestrator | HDO Data Available? | Can Migrate Now? |
|---|---|---|---|---|---|
| `identity` | 138 | `collectors.collect_identity()` | `collectors.collect_identity()` | ⚠️ Partial (DMI via EFI; MAC via network) | After new HDO slots |
| `firmware` | 139 | `collectors.collect_firmware()`, with `.secure_boot` overridden from `snapshot.secure_boot` when available (Beta M4) | `collectors.collect_firmware()` | ✅ `snapshot.secure_boot` (consumed, Beta M4); `snapshot.firmware_boot_configuration` still unconsumed | `.secure_boot`: ✅ **Done (Beta M4)**. Rest of `firmware` (`uefi`/`vendor`/`version`, `firmware_boot_configuration`): not migrated — no `HostInventory` field exists for the latter. |
| `operating_system` | 140 | `collectors.collect_operating_system()` | `collectors.collect_operating_system()` | ❌ None | After new HDO slot |
| `cpu` | 141 | `snapshot.cpu` (fallback to legacy) | `collectors.collect_cpu()` | ✅ `snapshot.cpu` | ✅ Already done |
| `memory` | 142 | `snapshot.memory` (fallback to legacy) | `collectors.collect_memory()` | ✅ `snapshot.memory` | ✅ Already done |
| `efi_system_partition` | 143 | `collectors.collect_efi_system_partition()` | `collectors.collect_efi_system_partition()` | ⚠️ Derived from `snapshot.storage_topology.devices[].partitions` | After new business service |
| `storage` | 144 | `_translate_storage_devices(snapshot.storage_topology)` (fallback to legacy) | `collectors.collect_storage()` | ✅ `snapshot.storage_topology` | ✅ **Done in #70** |
| `usb_storage` | 145 | `collectors.collect_usb_storage()` | `collectors.collect_usb_storage()` | ⚠️ Derived from `snapshot.storage_topology.devices[].is_removable` | After new filter function |
| `network` | 146 | `_translate_network_interfaces(snapshot.network)` (fallback to legacy, Beta M3 — was `list(snapshot.network)` pre-M3, before the slot was retyped to the real Network Adapter's model) | `collectors.collect_network()` | ✅ `snapshot.network` | ✅ **Done (Beta M3)** |
| `tooling` | 147 | `collectors.collect_tooling()` | `collectors.collect_tooling()` | ❌ None | After new HDO slot |

**Summary:** 2 fields source from HDO with no fallback shape change needed (`cpu`, `memory`); 3 source from HDO via a translate-or-fallback helper (`storage` — #70, `network` — Beta M3, `firmware.secure_boot` — Beta M4); 5 still unconditionally source from legacy collectors.

---

## 3. `HostDiscoverySnapshot` — Field Producer/Consumer Audit

Source code: `discovery/models.py:93-166`

| Field | Producer | Type | Consumer | Reaches CLI? | Status |
|---|---|---|---|---|---|
| `firmware_boot_configuration` | EFI adapter (`efibootmgr`) | `FirmwareBootConfiguration \| None` | **None** | ❌ | **Dead output.** Adapter runs, data is produced, nobody reads it. |
| `storage_topology` | Storage adapter (`lsblk`/`blkid`/`findmnt`) | `StorageConfiguration \| None` | `service.py:131` (#70) | ✅ via `HostInventory.storage` | ✅ Consumed |
| `secure_boot` | Secure Boot adapter (`mokutil`) | `SecureBootStatus \| None` | `service.py` `_translate_secure_boot_state()` (Beta M4) | ✅ via `HostInventory.firmware.secureBoot` | ✅ Consumed (`bcs inventory`); `bcs doctor` also consumes it, but via a direct adapter call, not this snapshot field |
| `filesystem` | Filesystem adapter (`df`) | `FilesystemUsageReport \| None` | **None** | ❌ | **Dead output + wasted subprocess.** Adapter runs `df`, data is thrown away. |
| `network` | Network adapter (`ip -json addr show`, Beta M3) | `NetworkInterfaceStatus \| None` | `service.py` `_translate_network_interfaces()` | ✅ via `HostInventory.network` | ✅ Consumed (from the real Network Adapter as of Beta M3, not the legacy collector - the legacy `collect_network()` is now only the fallback) |
| `cpu` | `collect_cpu()` (legacy) | `CpuInfo \| None` | `service.py:127` | ✅ via `HostInventory.cpu` | ✅ Consumed |
| `memory` | `collect_memory()` (legacy) | `MemoryInfo \| None` | `service.py:128` | ✅ via `HostInventory.memory` | ✅ Consumed |
| `tpm` | No adapter exists | `object \| None` | **None** | ❌ | Always `None` — expected |
| `caveats` | Orchestrator (error aggregation) | `tuple[str, ...]` | **None** | ❌ | **Dead output.** Adapter error information is collected but never exposed to the user. |

**Dead output count:** 2 of 9 fields (`firmware_boot_configuration`, `filesystem`) are produced by real subprocess execution and then completely unused (`caveats` is aggregation-only, not a subprocess call, but is also currently unexposed). `storage_topology`/`network`/`secure_boot` are all consumed as of issue #70/Beta M3/Beta M4.

---

## 4. Migration Roadmap

### Migration 1 — Doctor Wiring (HIGHEST PRIORITY)

**Current state:** `commands/doctor.py` imports 6 collectors directly (lines 29–36) and calls them in 7 check functions. `doctor.py` ignores the orchestrator entirely.

**Target state, as originally proposed here:** `run_doctor()` calls `runtime.host_discovery_orchestrator.discover()` once, stores the snapshot, and every `_check_*` function reads from it.

**Correction (Beta M4):** the proposal above conflicts with [ADR-0011 § Alternatives Considered](decisions/0011-host-discovery-orchestrator.md#alternatives-considered), which explicitly rejected exactly this shape for `bcs doctor` — a single check must never pay for, or be blocked by, an unrelated domain's adapter call, which a shared one-`discover()`-per-invocation sweep would violate. `_check_secure_boot()` was fixed (Beta M4) using the alternative the ADR does sanction instead: each check reads its own single collector/adapter directly (`read_secure_boot_status(runtime.command_runner)`), not a shared snapshot. This "Migration 1" section's general proposal needs reconciling with that ADR before any further check is migrated this way — see `docs/SECURE_BOOT_IMPLEMENTATION_PLAN.md` for the investigation that surfaced this.

**Dependencies:** None (orchestrator is already built and wired).

**Complexity:** Medium — 7 checks to refactor (6 remaining; `secure-boot` done).

**Risk:** Medium — check logic must remain behaviourally identical.

```
+-------------------------------+---------------------+---------------------+
| Check Function                | Current Source      | Future Source       |
+-------------------------------+---------------------+---------------------+
| _check_firmware()             | collect_firmware()  | snapshot.firmware_  |
|                               |                     | boot_configuration  |
| _check_secure_boot()          | ✅ DONE (M4): read_ | read_secure_boot_   |
|                               | secure_boot_status()| status(runtime.     |
|                               | via command_runner  | command_runner) -   |
|                               | directly, not the   | already the Future  |
|                               | snapshot (see note  | Source shown here   |
|                               | above)              |                     |
| _check_storage()              | collect_storage()   | snapshot.storage_   |
|                               |                     | topology.devices    |
| _check_esp()                  | collect_efi_system_ | snapshot.storage_   |
|                               | partition()         | topology (partition |
|                               |                     | filter by PARTTYPE) |
| _check_usb_storage()          | collect_usb_storage()| snapshot.storage_   |
|                               |                     | topology (filter    |
|                               |                     | by is_removable)    |
| _check_network()              | collect_network()   | snapshot.network    |
| _check_tooling()              | collect_tooling()   | snapshot.tooling or |
|                               |                     | stays as is         |
+-------------------------------+---------------------+---------------------+
```

**Estimated diff:** ~80 lines changed in `doctor.py`, ~100 lines new tests in `test_commands_doctor.py`.

### Migration 2 — Firmware Migration in `service.py`

**Current state:** `service.py:139` always calls `collectors.collect_firmware()` even when orchestrator is given.

**Target state:** When orchestrator is given, source `HostInventory.firmware` from `snapshot.firmware_boot_configuration` and `snapshot.secure_boot`:

```python
if orchestrator is not None:
    snapshot = orchestrator.discover()
    fw = snapshot.firmware_boot_configuration
    sb = snapshot.secure_boot
    firmware = FirmwareInfo(
        uefi=fw is not None,                          # EFI adapter returned data = UEFI present
        secure_boot=_to_inventory_secure_boot(sb),    # SecureBootStatus → SecureBootState
    )
else:
    firmware = collectors.collect_firmware()
```

**Dependencies:** None — EFI and Secure Boot adapters already produce data.

**Complexity:** Low — ~15 lines new mapping function.

**Risk:** Low — fallback to legacy when snapshot fields are None.

**Outcome:** Removes the last `UNKNOWN`-always Secure Boot path from `collect_host_inventory`.

### Migration 3 — Network Adapter Wiring (M3) ✅ DONE

**Status:** Complete (Beta M3). `app.py` now binds the Network Adapter (`read_network_interfaces`) via the composition root. Real IP addresses appear in `bcs inventory` output for the first time. The legacy `collect_network()` remains as a fallback when the adapter slot is unset or fails, and is marked with a ``.. deprecated::`` RST comment.

**Outcome:** IP addresses appear in `bcs inventory` for the first time. `doctor.py`'s `_check_network` also gets real IP data (after Migration 1).

### Migration 4 — ESP Business Logic

**Current state:** `service.py:143` always calls `collectors.collect_efi_system_partition()`.

**Target state:** New function `_detect_esp(storage: StorageConfiguration) -> EfiSystemPartition` scans `storage.devices[].partitions` for PARTTYPE `c12a7328-f81f-11d2-ba4b-00a0c93ec93b`.

**Dependencies:** Migration 1 (doctor) or at least the storage adapter path must be stable.

**Complexity:** Medium — needs GPT PARTUUID knowledge, handling conventions different from `/boot/efi`.

**Risk:** Medium — first business-logic layer on adapter data.

### Migration 5 — USB Storage Filter

**Current state:** `service.py:145` always calls `collectors.collect_usb_storage()`.

**Target state:** New filter function `_detect_usb_devices(storage: StorageConfiguration) -> list[UsbStorageDevice]` filters `devices` where `is_removable == True` and resolves vendor/model from adapter data.

**Dependencies:** Migration 1 (doctor) or at least storage adapter path stable.

**Complexity:** Low — straightforward list filter + field mapping.

**Risk:** Low — `is_removable` may match SD readers (same ambiguity legacy collector had with sysfs path checks).

### Migration 6 — Identity Source from Adapters

**Current state:** `service.py:138` always calls `collectors.collect_identity()`.

**Target state:** Source `dmi_product_uuid` from `snapshot.firmware_boot_configuration.smbios` (if available) and `primary_mac_address` from `snapshot.network`.

**Dependencies:** Migration 2 (firmware from HDO) + Migration 1 (doctor).

**Complexity:** Low — two field reads.

**Risk:** Low — fallback to legacy when None.

### Migration 7 — New HDO Slots (OS, Tooling)

**Current state:** `operating_system` and `tooling` are not in `HostDiscoveryAdapters` at all.

**Target state:** Add two new slots to `HostDiscoveryAdapters`/`HostDiscoverySnapshot`:

```python
# discovery/models.py
operating_system: Callable[[], OperatingSystemInfo] | None = None
tooling: Callable[[], list[ToolStatus]] | None = None
```

**Dependencies:** None — no adapter design needed, both are pure Python.

**Complexity:** Low — ~10 lines model changes, 3 lines composition root binding.

**Risk:** Low — both are pure stdlib.

---

## 5. Dependency Graph

```
Parallel (can run simultaneously):
  ├── Migration 1 (doctor.py)
  ├── Migration 3 (Network Adapter wiring)
  ├── Migration 7 (new HDO slots)

Sequential (each depends on previous):
  └── Migration 2 (firmware)
        └── Migration 6 (identity) — depends on Migration 2

Depends on stable storage:
  └── Migration 4 (ESP)     — depends on storage adapter path
  └── Migration 5 (USB)     — depends on storage adapter path

Zero-dependency independent:
  └── Migration 7 (OS + Tooling slots) — can be done at any time
```

**Claude Code parallelisation:** Migrations 1, 3, and 7 have no mutual dependencies and can be implemented by separate agents simultaneously. Migrations 4 and 5 wait for Migration 1 but can be parallelised with each other. Migration 2 and 6 form a sequential chain.

---

## 6. Technical Debt Register

### HIGH

| Debt | Location | Impact |
|---|---|---|
| **Filesystem adapter runs but its output is discarded** | `app.py:217` + `discovery/models.py:138` | Wasted subprocess (`df`) on every `bcs` invocation. Produces `HostDiscoverySnapshot.filesystem` that no code reads. |
| ~~**Secure Boot adapter runs but its output is discarded**~~ **Resolved (Beta M4)** | `app.py:216` (composition root) | Real Secure Boot state now reaches both `bcs inventory` (`HostInventory.firmware.secureBoot`, via the orchestrator) and `bcs doctor` (`_check_secure_boot()`, via a direct `read_secure_boot_status(runtime.command_runner)` call) — see `docs/SECURE_BOOT_IMPLEMENTATION_PLAN.md`. |
| **`doctor.py` mostly bypasses orchestrator/adapters** | `commands/doctor.py:29-49,106-121` | `bcs doctor` and `bcs inventory` read different data sources for `storage`/`esp`/`network`/`usb-storage`/`tooling`/`firmware`. The `secure-boot` check no longer has this problem (Beta M4, reads the same underlying adapter `bcs inventory` does, just via a separate call) — the module docstring was corrected to no longer claim uniform agreement across every check. The `network` check still reads `collect_network()` directly (legacy) while inventory reads from the Network Adapter — same-data guarantee not reached until Migration 1. |
| **Caveats are collected but never exposed** | `discovery/orchestrator.py:93-102` + `discovery/models.py:158-166` | If an adapter fails, the error is recorded in `caveats` but no command displays it. Silent failures. |

### MEDIUM

| Debt | Location | Impact |
|---|---|---|
| ~~**Network Adapter implemented but not wired**~~ **Resolved (Beta M3)** | `bcs/platform/adapters/network/` | Wired into the composition root's `network` slot; `bcs inventory` reports real IP addresses via the Host Discovery Orchestrator, falling back to the legacy collector when unavailable. |
| **Duplicate null-MAC constant** | `collectors.py:59` and `network/parser.py:40` | Both define `_NULL_MAC = "00:00:00:00:00:00"` independently. |
| **`_read_text()` is a generic utility trapped in `collectors.py`** | `collectors.py:70-76` | Cannot be imported by platform adapters. If the Filesystem adapter (or any future adapter) needs it, the utility must be extracted or duplicated. |
| **Legacy `_read_secure_boot_state()` always returns `UNKNOWN`** | `collectors.py:86-92` | Still true of the function itself (unchanged) - but it is now only the *fallback* path (Beta M4), used when the Secure Boot Adapter is unavailable; the primary path reports real state. |
| **`collect_storage()` still exists as dead fallback** | `collectors.py:95-119` | After doctor migrates, this function will only be called when the storage adapter slot is unset or fails — a rare edge case that nonetheless requires maintaining 380 lines of collector code. Marked with ``.. deprecated::`` RST comment. |

### LOW

| Debt | Location | Impact |
|---|---|---|
| **`collect_firmware()` reads `/sys/firmware/efi` twice per doctor run** | `commands/doctor.py:51,58` | `_check_firmware()` and `_check_secure_boot()` both call `collect_firmware()`, which checks the same sysfs directory twice. No caching. |
| **`commands/doctor.py` `_ALL_CHECKS` registry ignores `runtime` for 7 of 9 checks** | `commands/doctor.py:149-158` | The lambdas accept `_runtime` and discard it. Misleading API — all refactoring in the doctor migration will change this. |
| **`_parent_disk()` regex is duplicated from Storage Adapter** | `collectors.py:149-157` | The Storage Adapter's parser (`parse_storage_topology`) derives parent disks from `lsblk -J`'s JSON tree, not regex. The regex approach is narrower. |
| **`cli/tests/fixtures/` directory placeholder files** | `cli/tests/fixtures/{firmware,storage,secureboot,network}/` | All fixture files are zero-byte placeholders. No real hardware output has been captured for parser/adapter integration tests. |

---

## 7. Collector Fate Summary

| Collector | Fate | Reason | Removal Trigger |
|---|---|---|---|---|
| `collect_firmware()` | **Delete** | Replaced by EFI + Secure Boot adapters | After Migration 2 |
| `collect_storage()` | **Delete (Category B)** | Replaced by Storage adapter. Marked with ``.. deprecated::`` RST comment. | After doctor migrates |
| `collect_efi_system_partition()` | **Delete** | Replaced by new ESP business service | After Migration 4 |
| `collect_usb_storage()` | **Delete** | Replaced by `is_removable` filter | After Migration 5 |
| `collect_identity()` | **Delete** | Replaced by EFI + network adapter data | After Migration 6 |
| `collect_operating_system()` | **Keep as HDO slot** | Pure stdlib, like cpu/memory | Never |
| `collect_cpu()` | **Keep as HDO slot** | Pure stdlib | Never |
| `collect_memory()` | **Keep as HDO slot** | Pure stdlib | Never |
| `collect_network()` | **Delete (Category B)** | Replaced by Network Adapter (wired in Beta M3). Marked with ``.. deprecated::`` RST comment. | After Migration 1 (doctor) |
| `collect_tooling()` | **Keep as HDO slot** | Pure stdlib | Never |

---

## 8. Recommended Sprint Plan

```
Sprint 1 (highest value)
  Migration 1 — Doctor wiring (doctor.py → orchestrator)
  Migration 7 — New HDO slots for OS + Tooling
  → Both independent, parallelisable

Sprint 2 (flesh out the HDO path)
  Migration 2 — Firmware from EFI adapter
  Migration 3 — Network Adapter wiring
  → Independent of each other

Sprint 3 (complete the inventory)
  Migration 4 — ESP business logic
  Migration 5 — USB storage filter
  Migration 6 — Identity from adapters
  → Parallel with each other; depend on Sprint 1+2

Sprint 4 (cleanup)
  Delete: collect_firmware, collect_network, collect_efi_system_partition,
          collect_usb_storage, collect_identity
  Keep:   collect_operating_system, collect_cpu, collect_memory, collect_tooling
  Fix:    Duplicate _NULL_MAC constant
  Fix:    Filesystem adapter dead output (remove from composition root or consume)
  Done:   Secure Boot adapter dead output — consumed directly (Beta M4, not via Migration 2's
          originally-proposed shared-snapshot approach; see § 4 Migration 1's correction note)
  Fix:    Caveats exposed in CLI output
```
