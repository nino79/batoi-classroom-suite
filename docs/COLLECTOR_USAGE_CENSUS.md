# Collector Usage Census — Legacy `bcs.inventory.collectors`

**Generated:** 2026-07-09
**Purpose:** Complete inventory of every legacy `collect_*` function in `cli/src/bcs/inventory/collectors.py`, describing current callers, adapter equivalents, migration status, and removal horizon. Prepared for the Beta-phase legacy collector deprecation arc (issue #78).

---

## Census Table

| # | Collector | Location | Lines | Production Callers | Test Callers | Adapter Equivalent | Adapter→Inventory Translation | Migrated? | Removal Milestone | Issue |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `collect_firmware()` | `collectors.py:79-83` | 5 | `service.py:176` (always), `doctor.py:93` (always, `_check_firmware`), `doctor.py:113` (always, `_check_secure_boot` gate) | `test_inventory_collectors.py` (3), `test_inventory_service.py` (2 patched) | ✅ EFI adapter (`read_firmware_boot_configuration`) for UEFI presence; ✅ Secure Boot adapter (`read_secure_boot_status`) for `secure_boot` | ⚠️ Partial — `secure_boot` is translated in `service.py:196-199` (`_translate_secure_boot_state`), but `uefi`/`vendor`/`version` have no adapter equivalent | ⚠️ Partial — `secure_boot` routed (Beta M4); `uefi` probe still collector-only | Not scheduled | — |
| 2 | `collect_storage()` | `collectors.py:95-111` | 17 | `service.py:181` (fallback only, no-orch path), `service.py:189` (fallback only, orch path), `doctor.py:156` (always, `_check_storage` fallback) | `test_inventory_collectors.py` (2), `test_inventory_service.py` (2 patched + 1 fallback) | ✅ Storage adapter (`read_storage_topology`) | ✅ `service.py:97-123` (`_translate_storage_devices`) | ✅ Fallback-only via inventory (issue #70); primary via doctor | Doctor migration | #78 |
| 3 | `collect_efi_system_partition()` | `collectors.py:114-137` | 24 | `service.py:208` (always), `doctor.py:166` (always, `_check_esp`) | `test_inventory_collectors.py` (4), `test_inventory_service.py` (1 patched) | ⚠️ None dedicated — derivable from Storage adapter's `BlockDevice.partitions` (filter by GPT PARTTYPE `c12a7328-f81f-11d2-ba4b-00a0c93ec93b`) | ❌ No translation function exists | ❌ Not migrated | New milestone (post-Beta) | #74 |
| 4 | `collect_usb_storage()` | `collectors.py:198-214` | 17 | `service.py:210` (always), `doctor.py:175` (always, `_check_usb_storage`) | `test_inventory_collectors.py` (4) | ⚠️ None dedicated — derivable from Storage adapter's `BlockDevice.is_removable` | ❌ No translation function exists | ❌ Not migrated | New milestone (post-Beta) | #75 |
| 5 | `collect_network()` | `collectors.py:258-289` | 32 | `service.py:180` (fallback only, no-orch path), `service.py:194` (fallback only, orch path), `doctor.py:197` (always, `_check_network` fallback) | `test_inventory_collectors.py` (2), `test_inventory_service.py` (3 patched) | ✅ Network adapter (`read_network_interfaces`) | ✅ `service.py:126-149` (`_translate_network_interfaces`) | ✅ Fallback-only via inventory (Beta M3); primary via doctor | Doctor migration | #78 |
| 6 | `collect_identity()` | `collectors.py:292-300` | 9 | `service.py:203` (always) | `test_inventory_collectors.py` (2), `test_inventory_service.py` (1 patched) | ⚠️ None dedicated — DMI UUID could come from EFI adapter; primary MAC from Network adapter | ❌ No translation function exists | ❌ Not migrated | Not scheduled | #76 |
| 7 | `collect_operating_system()` | `collectors.py:315-323` | 9 | `service.py:205` (always) | `test_inventory_collectors.py` (2), `test_inventory_service.py` (1 patched) | ❌ None planned — pure stdlib reads (`/etc/os-release` + `platform.uname`) | ❌ No translation function exists | ❌ Not migrated | **Keep** — pure Python, never deprecated | — |
| 8 | `collect_cpu()` | `collectors.py:357-363` | 7 | `service.py:178` (fallback only, no-orch path), `service.py:184` (fallback only, orch path) | `test_inventory_collectors.py` (2), `test_inventory_service.py` (5 patched) | ❌ None planned — pure stdlib reads (`/proc/cpuinfo` + `platform.machine`) | ❌ N/A — reused directly as HDO slot (`app.py:220`) | ✅ Already reused as HDO slot | **Keep** — pure Python, never deprecated | — |
| 9 | `collect_memory()` | `collectors.py:336-347` | 12 | `service.py:179` (fallback only, no-orch path), `service.py:185` (fallback only, orch path) | `test_inventory_collectors.py` (2), `test_inventory_service.py` (5 patched) | ❌ None planned — pure stdlib reads (`/proc/meminfo`) | ❌ N/A — reused directly as HDO slot (`app.py:221`) | ✅ Already reused as HDO slot | **Keep** — pure Python, never deprecated | — |
| 10 | `collect_tooling()` | `collectors.py:377-382` | 6 | `service.py:212` (always), `doctor.py:219` (always, `_check_tooling`) | `test_inventory_collectors.py` (1) | ❌ None planned — pure `shutil.which`, no subprocess | ❌ No translation function exists | ❌ Not migrated | **Keep** — pure Python, never deprecated | — |

---

## Classification Summary

### Category A — Migrated / Fallback-Only (3)
- `collect_storage()` — fallback-only via inventory (issue #70)
- `collect_network()` — fallback-only via inventory (Beta M3)
- `collect_firmware().secure_boot` — overridden via translation (Beta M4)

### Category B — Partially Migrated (1)
- `collect_firmware().uefi` — still collector-only for the UEFI-presence gate

### Category C — Not Migrated, No Adapter (3)
- `collect_efi_system_partition()` — needs business-logic service
- `collect_usb_storage()` — needs filter on existing adapter data
- `collect_identity()` — could derive from existing adapters

### Category D — Keep Indefinitely (4)
- `collect_cpu()` — reused as HDO slot, pure Python
- `collect_memory()` — reused as HDO slot, pure Python
- `collect_operating_system()` — pure Python, no subprocess
- `collect_tooling()` — pure Python, no subprocess

---

## Key Observations

1. **6 of 10 collectors remain primary (non-fallback) in production code** — every collector except `storage` and `network` is always called. The `collect_firmware().secure_boot` path is overridden post-hoc but the function still runs.
2. **3 collectors are dead-weight when orchestrator is available**: `collect_storage()`, `collect_network()` (fallback-only via inventory). On a healthy machine with all tools present, these run but their results are discarded.
3. **4 collectors will never need a tool-based adapter** — `cpu`, `memory`, `operating_system`, `tooling` are pure stdlib reads with no subprocess dependency.
4. **2 collectors could be replaced by business-logic services** that filter existing adapter output: `collect_efi_system_partition()` and `collect_usb_storage()` operate on the same data the Storage Adapter already produces, just with interpretive logic no adapter should own.
5. **`collect_firmware()` is the most-called legacy function** — invoked 3 times per `bcs doctor` invocation (once by `_check_firmware`, once by `_check_secure_boot`'s UEFI gate, and once by `collect_host_inventory`). The `_read_secure_boot_state()` private helper it calls always returns `UNKNOWN`.
