# HDO Migration Plan

Replace legacy proxy collectors with the Host Discovery Orchestrator.

## Status

- **Phase 0 target:** Dual-Read (both paths live, `collect_host_inventory()` reads from HDO; `doctor.py` still reads from legacy)
- **Phase 1 target:** Legacy removed; `HostInventory` filled entirely from `DiscoveryResult`; `doctor.py` reads from HDO

## 1. Field-by-Field Mapping

`models.HostInventory` left column, current collector/fallback middle, HDO path right.

### Identity

| Inventory Field | Legacy Source | HDO Source | HDO Field | Status |
|---|---|---|---|---|
| `primary_mac_address` | `collect_network()` → first non-loopback up iface MAC | `discovery.network_interfaces` | `mac_address` of first non-loopback up iface | ✅ Dual-read |
| `dmi_product_uuid` | `collect_identity()` → `dmidecode` | `discovery.dmi_product_uuid` | `dmi_product_uuid` | ✅ Dual-read |

### Firmware

| Inventory Field | Legacy Source | HDO Source | HDO Field | Status |
|---|---|---|---|---|
| `uefi` | `collect_firmware()` → `/sys/firmware/efi` | `discovery.firmware_boot_mode` | `== FirmwareBootMode.UEFI` | ✅ — unused by `collect_host_inventory` |
| `secure_boot` | `collect_firmware()` → sbctl | `discovery.secure_boot_status` | `SecureBootStatus` enum | ⏳ Dual-read available; doctor still calls legacy |

### Operating System

| Inventory Field | Legacy Source | HDO Source | HDO Field | Status |
|---|---|---|---|---|
| `name` | `collect_os()` → `os-release` | — | Not in HDO v1 | ❌ needs ADR or HDO extension |
| `architecture` | `collect_os()` → `uname -m` | — | Not in HDO v1 | ❌ needs ADR or HDO extension |
| `kernel` | `collect_os()` → `uname -r` | — | Not in HDO v1 | ❌ needs ADR or HDO extension |

### CPU

| Inventory Field | Legacy Source | HDO Source | HDO Field | Status |
|---|---|---|---|---|
| `model` | `collect_cpu()` | — | Not in HDO v1 | ❌ needs ADR or HDO extension |
| `architecture` | `collect_cpu()` | — | Not in HDO v1 | ❌ needs ADR or HDO extension |
| `logical_cores` | `collect_cpu()` | — | Not in HDO v1 | ❌ needs ADR or HDO extension |

### Memory

| Inventory Field | Legacy Source | HDO Source | HDO Field | Status |
|---|---|---|---|---|
| `total_bytes` | `collect_memory()` | — | Not in HDO v1 | ❌ needs ADR or HDO extension |

### EFI System Partition

| Inventory Field | Legacy Source | HDO Source | HDO Field | Status |
|---|---|---|---|---|
| `present` | `collect_efi_system_partition()` | `discovery.firmware_boot_mode` | `== UEFI` (implies ESP exists) | ✅ Dual-read |
| `partition` | `collect_efi_system_partition()` → `findmnt`/`lsblk` | `discovery.esp_info` | `partition` | ✅ Dual-read |
| `filesystem` | `collect_efi_system_partition()` → `lsblk -o FSTYPE` | `discovery.esp_info` | `filesystem` | ✅ Dual-read |
| `mounted` | `collect_efi_system_partition()` → `mount` | `discovery.esp_info` | `mounted` | ✅ Dual-read |
| `mount_point` | `collect_efi_system_partition()` → `findmnt` | `discovery.esp_info` | `mount_point` | ✅ Dual-read |

### Storage

| Inventory Field | Legacy Source | HDO Source | HDO Field | Status |
|---|---|---|---|---|
| `[].path` | `collect_storage()` → `lsblk` | `discovery.storage_devices` | `device_path` | ✅ Dual-read |
| `[].name` | `collect_storage()` → basename of path | `discovery.storage_devices` | → `basename(device_path)` | ✅ Dual-read |
| `[].is_nvme` | `collect_storage()` → `lsblk -o TRAN` | `discovery.storage_devices` | `transport == "nvme"` | ✅ Dual-read |

### USB Storage

| Inventory Field | Legacy Source | HDO Source | HDO Field | Status |
|---|---|---|---|---|
| `[].path` | `collect_usb_storage()` → `lsblk` | `discovery.usb_devices` | `device_path` | ✅ Dual-read |
| `[].name` | `collect_usb_storage()` → basename | `discovery.usb_devices` | → `basename(device_path)` | ✅ Dual-read |
| `[].model` | `collect_usb_storage()` → `lsblk -o MODEL` | — | Not mapped yet | ⚠️ needs mapping or fallback |
| `[].mounted` | `collect_usb_storage()` → `mount` | `discovery.usb_devices` | `mount_points` non-empty | ✅ Dual-read |

### Network

| Inventory Field | Legacy Source | HDO Source | HDO Field | Status |
|---|---|---|---|---|
| `[].name` | `collect_network()` → `netifaces` | `discovery.network_interfaces` | `name` | ✅ Dual-read |
| `[].mac_address` | `collect_network()` → `netifaces` | `discovery.network_interfaces` | `mac_address` | ✅ Dual-read |
| `[].is_loopback` | `collect_network()` → flags check | `discovery.network_interfaces` | `is_loopback` | ✅ Dual-read |
| `[].is_up` | `collect_network()` → flags check | `discovery.network_interfaces` | `is_up` | ✅ Dual-read |

### Tooling

| Inventory Field | Legacy Source | HDO Source | HDO Field | Status |
|---|---|---|---|---|
| `[].name` | `collect_tooling()` → hardcoded list | — | Not in HDO v1 | ❌ — needs HDO extension or stays legacy |
| `[].found` | `collect_tooling()` → `shutil.which` | — | Not in HDO v1 | ❌ — needs HDO extension or stays legacy |
| `[].path` | `collect_tooling()` → `shutil.which` | — | Not in HDO v1 | ❌ — needs HDO extension or stays legacy |

## 2. Migration Order (PR decomposition)

### PR 1: HDO Adapter for OS, CPU, Memory, Tooling

**Problem:** HDO has no adapter for these four domains. OS, CPU, and Memory are lightweight (`os-release`, `uname`, `/proc/meminfo`) — not worth a full architecture-cycle adapter each. Tooling (`shutil.which`) is purely Python, no subprocess.

**Recommendation:** Produce a single design doc (`docs/OS_CPU_MEMORY_ADAPTER.md`) covering all three, plus a discussion of whether Tooling belongs in the HDO at all (it has no hardware-probe character — it's a `$PATH` query). One ADR-free adapter (the pattern is already established). A combined `EnvironmentAdapter` (or keep three separate, one file each).

### PR 2: `doctor.py` Migrates to HDO (Dual-Read)

**Change:** `_check_firmware`, `_check_secure_boot`, `_check_storage`, `_check_esp`, `_check_usb_storage`, `_check_network`, `_check_tooling` — every check that currently calls a `collect_*` directly — instead calls the orchestrator once and reads from `DiscoveryResult`.

**Why this matters:** Today `bcs doctor` and `bcs inventory` can disagree. After this PR they read the same data.

**Test approach (see §4):** No new fixtures needed — `doctor.py` tests mock the collectors already. The same approach applies: mock `HostDiscoveryOrchestrator.collect()` and return a `DiscoveryResult`.

### PR 3: Remove Legacy Collectors

**Change:** Delete the `collect_*` functions that now exist in HDO. The `discovery/` directory becomes the single source of truth.

**Requires:** PR 1 and PR 2 to be merged first. `collect_host_inventory()` in `service.py` builds entirely from `DiscoveryResult`.

### PR 4: Remove Dual-Read from `service.py`

**Change:** `collect_host_inventory()` no longer calls legacy collectors at all. The `HostInventory` model is filled exclusively from `orchestrator.collect()` plus inlined fallbacks if an HDO adapter field is `None`.

## 3. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| HDO adapter for USB MODEL field missing | USB model shows blank | Add parsing to storage adapter (`lsblk -o +MODEL`) or add a `model` field to `StorageDevice` |
| OS/CPU/Memory adapter scope creep | PR 1 grows too large | Treat as separate adapters in one PR, not a monolithic "Environment adapter" |
| `doctor.py` dual-read still calls legacy under the hood | No actual dual-read fidelity | Forbid that: doctors must call orchestrator, not legacy, even if the orchestrator internally still calls legacy adapters |
| `dmi_product_uuid` — HDO gets it from EFI adapter `smbios` field, legacy from `dmidecode` | Two tools, same data, subtle differences | Accept both as equivalent if they agree on the test VM; document the approach in the migration plan |

## 4. Test Strategy (Minimal)

The `collect_host_inventory()` → `orchestrator.collect()` path is **already tested implicitly** by the platform adapter tests and the `test_orchestrate_collect` integration test in `test_orchestrator.py`. The test pyramid target is:

- **Unit tests for the field-mapping logic** in `service.py` (the merge function `_merge_discovery_into_inventory`). A single pytest file (`test_service_migration.py`) with:
  - A `DiscoveryResult` factory
  - `HostInventory` equality checks
  - Tests for each domain: identity, firmware, esp, storage, usb, network.
  - Explicit null-fallback tests: "if HDO returns None for X, the legacy default is preserved"

- **No new integration tests** for the platform adapters as part of migration — the existing `test_orchestrate_collect` already validates the HDO path end to end.

- **`doctor.py` migration tests** already exist in `test_doctor.py` — the same `mock` approach works; no new test infrastructure is required.

## 5. Rollback

The dual-read phase (after PR 2) means every deployment can toggle between old and new paths by flipping a single boolean (`runtime.use_hdo` or similar). This flag is provisional — it exists only during the dual-read window and is removed in PR 3.
