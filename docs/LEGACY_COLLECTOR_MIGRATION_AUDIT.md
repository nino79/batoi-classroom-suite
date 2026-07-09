# Legacy Collector Migration Audit

**Post-Issue #70 state.**

Issue #70 has landed: `bcs inventory` now passes the Host Discovery Orchestrator and
sources `storage` from the Storage Adapter with a fallback to the legacy collector.

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

### 1.2 `collect_storage()` — lines 95–102

| Attribute | Value |
|---|---|
| **Purpose** | Glob `/dev/nvme[0-9]n[0-9]` — only matches NVMe; misses SATA/SCSI |
| **Adapter equivalent** | ✅ **Storage adapter** (`read_storage_topology`) produces `StorageConfiguration` with all `BlockDevice` entries |
| **Adapter wired?** | ✅ Yes |
| **HDO slot** | `HostDiscoverySnapshot.storage_topology` |
| **Current callers** | `service.py:124,133` (fallback only), `doctor.py:74` (always) |
| **Used by CLI?** | `bcs inventory` — via HDO path after #70 ✅ |
| **Fallback available?** | ✅ Yes — implemented in #70 (`service.py:130-134`) |
| **Fate** | **Deprecated.** Called only as fallback from `service.py` and unconditionally from `doctor.py`. Can be removed after doctor migrates. |
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

### 1.9 `collect_network()` — lines 249–272

| Attribute | Value |
|---|---|
| **Purpose** | Read `/sys/class/net/*/address` + `operstate`; `ip_addresses` always `[]` (placeholder) |
| **Adapter equivalent** | ✅ **Network adapter** (`read_network_interfaces`) — fully implemented, 100% tested, produces `NetworkInterfaceStatus` with real IP addresses |
| **Adapter wired?** | ❌ **No.** `app.py:218` binds `collectors.collect_network` directly, NOT the Network Adapter. |
| **HDO slot** | `HostDiscoverySnapshot.network` |
| **Current callers** | `service.py:123,129` (HDO path), `doctor.py:99` (legacy) |
| **Used by CLI?** | ✅ Yes — but `ip_addresses` is always empty |
| **Fallback available?** | No fallback needed — network has no required-field constraint |
| **Fate** | **Deprecate.** Replace with Network Adapter in the composition root. |
| **Beta milestone** | M3 |

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
| `firmware` | 139 | `collectors.collect_firmware()` | `collectors.collect_firmware()` | ✅ `snapshot.firmware_boot_configuration` + `snapshot.secure_boot` | **Yes** — no new adapter needed |
| `operating_system` | 140 | `collectors.collect_operating_system()` | `collectors.collect_operating_system()` | ❌ None | After new HDO slot |
| `cpu` | 141 | `snapshot.cpu` (fallback to legacy) | `collectors.collect_cpu()` | ✅ `snapshot.cpu` | ✅ Already done |
| `memory` | 142 | `snapshot.memory` (fallback to legacy) | `collectors.collect_memory()` | ✅ `snapshot.memory` | ✅ Already done |
| `efi_system_partition` | 143 | `collectors.collect_efi_system_partition()` | `collectors.collect_efi_system_partition()` | ⚠️ Derived from `snapshot.storage_topology.devices[].partitions` | After new business service |
| `storage` | 144 | `_translate_storage_devices(snapshot.storage_topology)` (fallback to legacy) | `collectors.collect_storage()` | ✅ `snapshot.storage_topology` | ✅ **Done in #70** |
| `usb_storage` | 145 | `collectors.collect_usb_storage()` | `collectors.collect_usb_storage()` | ⚠️ Derived from `snapshot.storage_topology.devices[].is_removable` | After new filter function |
| `network` | 146 | `list(snapshot.network)` | `collectors.collect_network()` | ✅ `snapshot.network` | ✅ Already done |
| `tooling` | 147 | `collectors.collect_tooling()` | `collectors.collect_tooling()` | ❌ None | After new HDO slot |

**Summary:** 3 fields already source from HDO (cpu, memory, network); 1 now sources from HDO (#70 storage); 6 still unconditionally source from legacy collectors.

---

## 3. `HostDiscoverySnapshot` — Field Producer/Consumer Audit

Source code: `discovery/models.py:93-166`

| Field | Producer | Type | Consumer | Reaches CLI? | Status |
|---|---|---|---|---|---|
| `firmware_boot_configuration` | EFI adapter (`efibootmgr`) | `FirmwareBootConfiguration \| None` | **None** | ❌ | **Dead output.** Adapter runs, data is produced, nobody reads it. |
| `storage_topology` | Storage adapter (`lsblk`/`blkid`/`findmnt`) | `StorageConfiguration \| None` | `service.py:131` (#70) | ✅ via `HostInventory.storage` | ✅ Consumed |
| `secure_boot` | Secure Boot adapter (`mokutil`) | `SecureBootStatus \| None` | **None** | ❌ | **Dead output.** Real data is produced (not `UNKNOWN`), nobody reads it. |
| `filesystem` | Filesystem adapter (`df`) | `FilesystemUsageReport \| None` | **None** | ❌ | **Dead output + wasted subprocess.** Adapter runs `df`, data is thrown away. |
| `network` | `collect_network()` (legacy, NOT Network Adapter) | `tuple[NetworkInterface, ...]` | `service.py:129` | ✅ via `HostInventory.network` | ✅ Consumed (but from legacy, not the real adapter) |
| `cpu` | `collect_cpu()` (legacy) | `CpuInfo \| None` | `service.py:127` | ✅ via `HostInventory.cpu` | ✅ Consumed |
| `memory` | `collect_memory()` (legacy) | `MemoryInfo \| None` | `service.py:128` | ✅ via `HostInventory.memory` | ✅ Consumed |
| `tpm` | No adapter exists | `object \| None` | **None** | ❌ | Always `None` — expected |
| `caveats` | Orchestrator (error aggregation) | `tuple[str, ...]` | **None** | ❌ | **Dead output.** Adapter error information is collected but never exposed to the user. |

**Dead output count:** 4 of 9 fields (firmware_boot_configuration, secure_boot, filesystem, caveats) are produced by real subprocess execution and then completely unused.

---

## 4. Migration Roadmap

### Migration 1 — Doctor Wiring (HIGHEST PRIORITY)

**Current state:** `commands/doctor.py` imports 6 collectors directly (lines 29–36) and calls them in 7 check functions. `doctor.py` ignores the orchestrator entirely.

**Target state:** `run_doctor()` calls `runtime.host_discovery_orchestrator.discover()` once, stores the snapshot, and every `_check_*` function reads from it.

**Dependencies:** None (orchestrator is already built and wired).

**Complexity:** Medium — 7 checks to refactor.

**Risk:** Medium — check logic must remain behaviourally identical.

```
+-------------------------------+---------------------+---------------------+
| Check Function                | Current Source      | Future Source       |
+-------------------------------+---------------------+---------------------+
| _check_firmware()             | collect_firmware()  | snapshot.firmware_  |
|                               |                     | boot_configuration  |
| _check_secure_boot()          | collect_firmware()  | snapshot.secure_boot|
|                               | (reads /sys twice!) |                     |
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

### Migration 3 — Network Adapter Wiring (M3)

**Current state:** `app.py:218` binds `collectors.collect_network`. The Network Adapter (`read_network_interfaces`) is implemented and tested but not wired.

**Target state:** `app.py:218` binds `functools.partial(read_network_interfaces, runner=command_runner)`.

**Dependencies:** Model translation layer — the Network Adapter's `NetworkInterface` model is independently defined from `inventory.models.NetworkInterface`. A `_translate_network_interfaces()` function is needed.

**Complexity:** Low — 2 lines changed in `app.py`, ~20 lines translation function in `service.py`.

**Risk:** Low — network has no required fields; empty result is valid.

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
| **Secure Boot adapter runs but its output is discarded** | `app.py:216` + `discovery/models.py:133` | Wasted subprocess (`mokutil`) on every `bcs` invocation. Real Secure Boot state is collected but never reaches the user — `collect_firmware()` always returns `UNKNOWN`. |
| **`doctor.py` bypasses orchestrator entirely** | `commands/doctor.py:29-36,50-121` | `bcs doctor` and `bcs inventory` read different data sources. The docstring at line 12 claims they cannot disagree, but this is false. |
| **Caveats are collected but never exposed** | `discovery/orchestrator.py:93-102` + `discovery/models.py:158-166` | If an adapter fails, the error is recorded in `caveats` but no command displays it. Silent failures. |

### MEDIUM

| Debt | Location | Impact |
|---|---|---|
| **Network Adapter implemented but not wired** | `bcs/platform/adapters/network/` | 4 files, ~450 lines of tested code that is never loaded at runtime. IP addresses remain empty. |
| **Duplicate null-MAC constant** | `collectors.py:59` and `network/parser.py:40` | Both define `_NULL_MAC = "00:00:00:00:00:00"` independently. |
| **`_read_text()` is a generic utility trapped in `collectors.py`** | `collectors.py:70-76` | Cannot be imported by platform adapters. If the Filesystem adapter (or any future adapter) needs it, the utility must be extracted or duplicated. |
| **Legacy `_read_secure_boot_state()` always returns `UNKNOWN`** | `collectors.py:86-92` | This is a documented placeholder. The real implementation exists in the Secure Boot adapter but is not connected. |
| **`collect_storage()` still exists as dead fallback** | `collectors.py:95-102` | After doctor migrates, this function will only be called when the storage adapter slot is unset or fails — a rare edge case that nonetheless requires maintaining 380 lines of collector code. |

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
|---|---|---|---|
| `collect_firmware()` | **Delete** | Replaced by EFI + Secure Boot adapters | After Migration 2 |
| `collect_storage()` | **Delete** | Replaced by Storage adapter | After doctor migrates |
| `collect_efi_system_partition()` | **Delete** | Replaced by new ESP business service | After Migration 4 |
| `collect_usb_storage()` | **Delete** | Replaced by `is_removable` filter | After Migration 5 |
| `collect_identity()` | **Delete** | Replaced by EFI + network adapter data | After Migration 6 |
| `collect_operating_system()` | **Keep as HDO slot** | Pure stdlib, like cpu/memory | Never |
| `collect_cpu()` | **Keep as HDO slot** | Pure stdlib | Never |
| `collect_memory()` | **Keep as HDO slot** | Pure stdlib | Never |
| `collect_network()` | **Delete** | Replaced by Network Adapter | After Migration 3 |
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
  Fix:    Secure Boot adapter dead output (consumed via Migration 2)
  Fix:    Caveats exposed in CLI output
```
