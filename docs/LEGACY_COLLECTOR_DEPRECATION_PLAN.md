# Legacy Collector Deprecation Plan

**Phase:** Beta migration — after Issue #70 has landed.

**Goal:** Retire every legacy `bcs.inventory.collectors` function that has a Host Discovery
Orchestrator replacement, while keeping the four pure-Python collectors that will be
reused as HDO adapter callables indefinitely.

---

## 1. Inventory of All Collectors

For the full census — purpose, lines, callers, adapter equivalent, all 12 private helpers,
and every module-level constant — see the companion file
[docs/COLLECTOR_USAGE_CENSUS.md](COLLECTOR_USAGE_CENSUS.md) (generated from the architectural audit
that produced this plan). This document covers only the removal strategy.

### 1.1 Migrate — Replace with HDO Adapter

| Collector | Replacement | PR/Issue |
|---|---|---|
| `collect_firmware()` | `HostDiscoverySnapshot.firmware_boot_configuration` + `secure_boot` | #71 (doctor wiring), #73 (service) |
| `collect_storage()` | `HostDiscoverySnapshot.storage_topology.devices` | #70 (in progress) |
| `collect_efi_system_partition()` | New business-logic service on `storage_topology.devices[].partitions` filtered by GPT PARTUUID | #74 |
| `collect_usb_storage()` | `BlockDevice.is_removable` filter on `storage_topology.devices` | #75 |
| `collect_identity()` | EFI adapter `smbios` field + network adapter MAC | #76 |
| `collect_network()` | `read_network_interfaces()` (Network Adapter, already implemented) | #72 |

### 1.2 Keep — Pure-Python, Reused by HDO Slot

| Collector | Rationale |
|---|---|
| `collect_operating_system()` | Reads `/etc/os-release` + `platform.uname()` — no subprocess, no privilege. |
| `collect_cpu()` | Reads `/proc/cpuinfo` + `os.cpu_count()` — no subprocess. |
| `collect_memory()` | Reads `/proc/meminfo` — no subprocess. |
| `collect_tooling()` | `shutil.which()` — no subprocess, no hardware probe. |

These four are kept as both the HDO slot binding (already the case for `cpu`/`memory`;
`network` will be replaced; `tooling`/`operating_system` have no HDO slot today and
should be added as lightweight slots).

---

## 2. Migration Phases

### Phase A — Command Wiring (after #70)

| Step | Change | Files | Effort |
|---|---|---|---|
| A1 | `bcs inventory` passes `runtime.host_discovery_orchestrator` | `commands/inventory.py:135` | Trivial |
| A2 | `bcs doctor` consumes snapshot for all checks | `commands/doctor.py` (7 checks) | 3 days |
| A3 | Add `collect_operating_system` / `collect_tooling` as HDO adapter slots | `discovery/models.py`, `app.py`, `service.py` | 1 day |

**Exit criteria:** Both commands read from the same `DiscoveryResult`. Storage, CPU,
memory, network, and (when wired) firmware/Secure Boot converge.

### Phase B — Storage Adapter Integration (Issue #70)

| Step | Change | Files | Effort |
|---|---|---|---|
| B1 | `BlockDevice` → `StorageDevice` translation | `inventory/service.py` | 1 day |
| B2 | Wire command to pass orchestrator | `commands/inventory.py` | Trivial |
| B3 | Tests for translation + fallback | `tests/test_inventory_service.py` | 1 day |

**Exit criteria:** `bcs inventory` reports SATA and NVMe disks.

### Phase C — Network Adapter Wiring

| Step | Change | Files | Effort |
|---|---|---|---|
| C1 | Narrow `HostDiscoveryAdapters.network` type to `NetworkInterfaceStatus` | `discovery/models.py` | Trivial |
| C2 | Replace `collect_network` with `read_network_interfaces` in composition root | `app.py` | Trivial |
| C3 | Add model translation layer (Platform→Inventory `NetworkInterface`) | `inventory/service.py` | 1 day |
| C4 | Update doctor's `_check_network` | `commands/doctor.py` | 1 day |

**Exit criteria:** IP addresses appear in `bcs inventory` output.

### Phase D — Firmware, Identity, ESP, USB Migration

| Step | Change | Files | Effort |
|---|---|---|---|
| D1 | Map `FirmwareBootConfiguration` → `FirmwareInfo.uefi` and `SecureBootStatus` → `SecureBootState` | `inventory/service.py` | 1 day |
| D2 | Map EFI adapter `smbios.dmi_product_uuid` → `HostIdentity.dmi_product_uuid` | `inventory/service.py` | 1 day |
| D3 | Implement ESP detection: filter `storage_topology.devices[].partitions` by PARTTYPE GUID `c12a7328-f81f-11d2-ba4b-00a0c93ec93b` | `inventory/service.py` or new `esp.py` | 2 days |
| D4 | Implement USB detection: filter `storage_topology.devices` by `is_removable` | `inventory/service.py` | 1 day |

**Exit criteria:** All `HostInventory` fields sourced from HDO. No legacy collectors
called from `collect_host_inventory()`.

### Phase E — Collector Removal

| Step | Remove | Files | Risk |
|---|---|---|---|
| E1 | `collect_firmware()` + `_read_secure_boot_state()` | `inventory/collectors.py` | Low — EFI + Secure Boot adapters are stable |
| E2 | `collect_storage()` | `inventory/collectors.py` | Low — dual-read has been running |
| E3 | `collect_efi_system_partition()` + `_read_esp_mount()`, `_parent_disk()`, `_partition_uuid()`, `_partition_usage()` | `inventory/collectors.py` | Medium — ESP business logic newly implemented |
| E4 | `collect_usb_storage()` + `_is_usb_removable()`, `_read_usb_storage_device()`, `_find_mounted_partition()` | `inventory/collectors.py` | Low — simple `is_removable` filter |
| E5 | `collect_identity()` + `_primary_mac_address()` | `inventory/collectors.py` | Low — two field reads from existing adapters |
| E6 | `collect_network()` | `inventory/collectors.py` | Low — Network Adapter is fully tested |

**Exit criteria:** `bcs.inventory.collectors` contains only the four permanent collectors
(`collect_operating_system`, `collect_cpu`, `collect_memory`, `collect_tooling`) plus
`_read_text`, `_read_cpu_model`, `_read_os_release_pretty_name`, `_parse_meminfo_kb_line`,
and `_parent_disk` (the last as a cross-module utility).

---

## 3. Dual-Read Safety

Every migration in Phases B–D must implement the **fallback pattern** already established
for CPU and memory in `service.py`:

```python
storage = (
    _translate_storage_devices(snapshot.storage_topology.devices)
    if snapshot.storage_topology is not None
    else collectors.collect_storage()
)
```

This guarantees:
- **No crash** if an adapter slot is unwired or fails (PlatformError → `None` in snapshot).
- **No silent data loss** if an adapter returns unexpected data (fallback to legacy).
- **Backward compatibility** for every deployment that has not yet wired the new adapter.

The dual-read flag `runtime.use_hdo` is **not** required — the fallback is implicit in
the `None`-check on each snapshot field.

---

## 4. Test Strategy

### 4.1 Existing Tests That Must Remain Passing

| Test File | What It Covers | Risk During Migration |
|---|---|---|
| `test_inventory_service.py` | `collect_host_inventory()` with/without orchestrator | Must extend, never break |
| `test_commands_inventory.py` | CLI output shapes (text, JSON, YAML) | Must remain byte-for-byte identical |
| `test_commands_doctor.py` | Check status logic (211 lines) | Must add HDO-sourced paths, keep legacy paths |
| `test_inventory_collectors.py` | All 10 collectors (432 lines) | Must keep until Phase E deletion |
| `test_host_discovery_pipeline.py` | Full HDO pipeline end-to-end | Unchanged |

### 4.2 New Tests Required

| Phase | New Tests | Scope |
|---|---|---|
| B | `test_translate_storage_devices` | `BlockDevice` → `StorageDevice` field mapping (6 tests) |
| C | `test_translate_network_interfaces` | Platform `NetworkInterface` → Inventory `NetworkInterface` |
| D | `test_detect_esp_from_storage` | PARTUUID filtering logic |
| D | `test_detect_usb_from_storage` | `is_removable` filter + sysfs path check |
| D | `test_firmware_boot_configuration_to_info` | `FirmwareBootConfiguration` → `FirmwareInfo` |

### 4.3 Collector Removal Test Updates

| Collector Removed | Tests Affected | Action |
|---|---|---|
| `collect_storage()` | `test_inventory_collectors.py:55-71` | Delete |
| `collect_firmware()` | `test_inventory_collectors.py:15-47` | Delete |
| `collect_efi_system_partition()` | `test_inventory_collectors.py:79-181` | Delete |
| `collect_usb_storage()` | `test_inventory_collectors.py:189-285` | Delete |
| `collect_identity()` | `test_inventory_collectors.py:327-349` | Delete |
| `collect_network()` | `test_inventory_collectors.py:300-319` | Delete |

After all deletions, `test_inventory_collectors.py` will shrink from 432 lines to ~100
lines (only the permanent collectors remain).

---

## 5. Dead Code to Clean Up During Migration

| Code | Where | When to Clean Up |
|---|---|---|
| `_NULL_MAC = "00:00:00:00:00:00"` | `collectors.py:59` | Phase E (identity removal) |
| `_NULL_MAC = "00:00:00:00:00:00"` | `network/parser.py:40` | When Network Adapter is next touched (consolidate into one shared constant) |
| Filesystem adapter `read_filesystem_usage` call | `app.py:217` | After deciding whether to keep or remove the adapter from the composition root |
| `HostDiscoverySnapshot.filesystem` field | `discovery/models.py:138` | Same as above |
| All 4 adapter design docs' "unwired" status banners | `docs/{EFI,STORAGE,SECURE_BOOT,FILESYSTEM,NETWORK}_ADAPTER.md` | Each phase as the adapter is wired |

---

## 6. Documentation Update Tracker

After every phase, the following documents must be updated:

| Document | Phase A | Phase B | Phase C | Phase D | Phase E |
|---|---|---|---|---|---|
| `IMPLEMENTATION_STATUS.md` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `HOST_DISCOVERY_ORCHESTRATOR.md` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `KNOWN_LIMITATIONS.md` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `HOST_INVENTORY.md` | — | ✅ | ✅ | ✅ | ✅ |
| `BETA_ROADMAP.md` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `CLI.md` | — | ✅ | ✅ | ✅ | ✅ |
| `HARDWARE_MATRIX.md` | — | ✅ | — | ✅ | ✅ |
| `REAL_WORLD_VALIDATION.md` | — | ✅ | — | ✅ | ✅ |
| `CHANGELOG.md` | ✅ | ✅ | ✅ | ✅ | ✅ |
| Adapter design docs status banners | — | ✅ | ✅ | ✅ | — |

---

## 7. Removed Function Archive

When a collector is deleted, its code should be preserved in the git history only.
No archive file is needed — git log is the archive. The commit message for each deletion
must reference:

- The collector being deleted
- The PR/issue that implemented its replacement
- The date range the collector was live (from first commit to deletion)
- Any migration command a user would need (none expected — all changes are internal)

Example commit message:

```
feat: remove collect_storage()

The Storage Adapter (read_storage_topology) has been the single source of
truth for HostInventory.storage since PR #70 (YYYY-MM-DD). The legacy
collector has been in dual-read fallback-only mode since that release
and is no longer called from any code path.

Removed: collect_storage() and its sole call site in service.py.
Kept:    _parent_disk() as a utility (still used by other collectors).
```

---

## 8. Rollback Plan

If a post-migration release shows a regression, the rollback is:

1. **Restore the deleted collector function** — git revert the deletion commit.
2. **Restore the call sites** — git revert the migration commit.
3. **Restore the import** — git revert the removal from `service.py`.

Because each collector removal is a separate commit, reverting one collector does not
affect any other. No data migration, no config change, no CLI compatibility break.
