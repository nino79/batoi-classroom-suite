# Legacy Collector Runtime Usage Analysis

**Post-Issue #70 and Beta M3 state.**

Determines which legacy `bcs.inventory.collectors` functions are still
executed at runtime — distinguishing primary paths, fallback paths,
doctor-only paths, and paths that are now dead code.

---

## 1. Runtime Execution Paths

There are three distinct execution paths by which a legacy collector
can be reached:

| Path | Triggered by | Calls legacy collectors? |
|---|---|---|
| **A: `bcs inventory` via HDO** | `run_inventory()` → `collect_host_inventory(orchestrator=...)` | **8 of 10** (identity, firmware, os, cpu, memory, esp, usb, tooling). Storage and network come from adapters. |
| **B: `bcs inventory` without HDO** | `collect_host_inventory(orchestrator=None)` | **10 of 10** (all collectors, no adapter path used). Currently unreachable from any command — the composition root always sets `host_discovery_orchestrator`. |
| **C: `bcs doctor`** | `run_doctor()` → calls collectors directly via 6 `_check_*` functions | **6 of 10** (firmware, storage, esp, usb, network, tooling). Doctor never passes an orchestrator. |

---

## 2. Per-Collector Analysis

### `collect_firmware()` (lines 79–83)

| Attribute | Value |
|---|---|
| **Lines** | 79–83 |
| **Public/private** | Public |
| **Runtime paths** | A (service.py:172), C (doctor.py:51,58) |
| **HDO equivalent** | EFI adapter (`firmware_boot_configuration`) + Secure Boot adapter (`secure_boot`) — both exist, both produce data, but no `HostInventory` schema field consumes either |
| **Called per `bcs inventory`** | 1 call |
| **Called per `bcs doctor`** | **2 calls** (both `_check_firmware` and `_check_secure_boot` call `collect_firmware()` independently — the function runs twice, reads `/sys/firmware/efi` twice) |
| **HDO slot exists?** | No (the `efi` adapter is separate; firmware has no HDO slot in `HostDiscoveryAdapters`) |
| **Private helpers called** | `_read_secure_boot_state()` |
| **Classification** | **Always primary** — no HDO-based alternative exists in the `HostInventory` schema today |

---

### `_read_secure_boot_state()` (lines 86–92)

| Attribute | Value |
|---|---|
| **Lines** | 86–92 |
| **Public/private** | Private |
| **Runtime paths** | Only via `collect_firmware()` at line 83 |
| **Callers** | `collect_firmware()` only |
| **HDO equivalent** | Secure Boot adapter (`read_secure_boot_status`) — fully implemented, wired at the composition root, produces real data that is never consumed by any command |
| **Classification** | **Private helper, always dead logic** — always returns `UNKNOWN` regardless of actual firmware state |

---

### `collect_storage()` (lines 95–102)

| Attribute | Value |
|---|---|
| **Lines** | 95–102 |
| **Public/private** | Public |
| **Runtime paths** | A (fallback only — service.py:161), C (doctor.py:74) |
| **HDO equivalent** | Storage adapter (`read_storage_topology`) — fully implemented, wired, produces `BlockDevice` data |
| **Called via path A** | Only if `snapshot.storage_topology is None` — which won't happen on real hardware with `lsblk` available |
| **Called via path C** | Always (doctor ignores HDO entirely) |
| **HDO slot exists?** | Yes — `storage` slot is bound to `functools.partial(read_storage_topology, runner=command_runner)` at app.py:216 |
| **Classification** | **Fallback-only via inventory, primary via doctor** |

---

### `collect_efi_system_partition()` (lines 105–128)

| Attribute | Value |
|---|---|
| **Lines** | 105–128 |
| **Public/private** | Public |
| **Runtime paths** | A (service.py:176), C (doctor.py:82) |
| **HDO equivalent** | None — could be derived from `snapshot.storage_topology.devices[].partitions` by filtering for GPT PARTTYPE `c12a7328-f81f-11d2-ba4b-00a0c93ec93b`, but no such business-logic function exists |
| **Called via path A** | Always (no HDO slot exists) |
| **Called via path C** | Always (doctor ignores HDO entirely) |
| **HDO slot exists?** | No |
| **Private helpers called** | `_read_esp_mount()`, `_parent_disk()`, `_partition_uuid()`, `_partition_usage()` |
| **Classification** | **Always primary** — no HDO-based alternative exists |

---

### `collect_usb_storage()` (lines 189–205)

| Attribute | Value |
|---|---|
| **Lines** | 189–205 |
| **Public/private** | Public |
| **Runtime paths** | A (service.py:178), C (doctor.py:91) |
| **HDO equivalent** | None — could be derived from `snapshot.storage_topology.devices` filtered by `is_removable`, but no such filter function exists |
| **Called via path A** | Always (no HDO slot exists) |
| **Called via path C** | Always (doctor ignores HDO entirely) |
| **HDO slot exists?** | No |
| **Private helpers called** | `_is_usb_removable()`, `_read_usb_storage_device()`, `_find_mounted_partition()` |
| **Classification** | **Always primary** — no HDO-based alternative exists |

---

### `collect_network()` (lines 249–272)

| Attribute | Value |
|---|---|
| **Lines** | 249–272 |
| **Public/private** | Public |
| **Runtime paths** | A (fallback only — service.py:166), C (doctor.py:99) |
| **HDO equivalent** | Network adapter (`read_network_interfaces`) — fully implemented, wired at composition root (app.py:219), produces `NetworkInterfaceStatus` with real IP addresses |
| **Called via path A** | Only if `snapshot.network is None` — won't happen on real hardware with `ip` available |
| **Called via path C** | Always (doctor ignores HDO entirely) |
| **HDO slot exists?** | Yes — `network` slot is bound to `functools.partial(read_network_interfaces, runner=command_runner)` at app.py:219 |
| **Classification** | **Fallback-only via inventory, primary via doctor** |

---

### `collect_identity()` (lines 275–283)

| Attribute | Value |
|---|---|
| **Lines** | 275–283 |
| **Public/private** | Public |
| **Runtime paths** | A (service.py:171) |
| **HDO equivalent** | None — though `dmi_product_uuid` could come from EFI adapter's `FirmwareBootConfiguration.smbios` and `primary_mac_address` from the Network Adapter's output |
| **Called via path A** | Always (no HDO slot exists) |
| **Called via path C** | **Never** (doctor doesn't check identity) |
| **HDO slot exists?** | No |
| **Private helpers called** | `_primary_mac_address()` |
| **Classification** | **Always primary via inventory, unused by doctor** |

---

### `collect_operating_system()` (lines 298–306)

| Attribute | Value |
|---|---|
| **Lines** | 298–306 |
| **Public/private** | Public |
| **Runtime paths** | A (service.py:173) |
| **HDO equivalent** | None — pure stdlib reads |
| **Called via path A** | Always (no HDO slot exists) |
| **Called via path C** | **Never** (doctor doesn't check OS) |
| **HDO slot exists?** | No |
| **Private helpers called** | `_read_os_release_pretty_name()` |
| **Classification** | **Always primary via inventory, unused by doctor** |

---

### `collect_memory()` (lines 319–330)

| Attribute | Value |
|---|---|
| **Lines** | 319–330 |
| **Public/private** | Public |
| **Runtime paths** | A (service.py:157 — fallback, but the HDO slot IS this same function) |
| **HDO equivalent** | None — no tool-based adapter. The HDO `memory` slot is bound directly to `collectors.collect_memory` at app.py:221 |
| **Called via path A with HDO** | **Always called** — the HDO slot (`memory`) invokes `collect_memory()` during `orchestrator.discover()`, then `snapshot.memory` is never `None`, so the fallback at line 157 is never reached. But the function was already called once by the HDO slot. |
| **Called via path B** | Always (no orchestrator) |
| **Called via path C** | **Never** (doctor doesn't check memory) |
| **HDO slot exists?** | Yes — but bound to `collectors.collect_memory` itself (same function) |
| **Classification** | **Always called, but never through a tool-based adapter** |

---

### `collect_cpu()` (lines 340–346)

| Attribute | Value |
|---|---|
| **Lines** | 340–346 |
| **Public/private** | Public |
| **Runtime paths** | A (service.py:156 — fallback, but the HDO slot IS this same function) |
| **HDO equivalent** | None — no tool-based adapter. The HDO `cpu` slot is bound directly to `collectors.collect_cpu` at app.py:220 |
| **Called via path A with HDO** | **Always called** — the HDO slot (`cpu`) invokes `collect_cpu()` during `orchestrator.discover()`, then `snapshot.cpu` is never `None`, so the fallback at line 156 is never reached. But the function was already called once by the HDO slot. |
| **Called via path B** | Always (no orchestrator) |
| **Called via path C** | **Never** (doctor doesn't check CPU) |
| **HDO slot exists?** | Yes — but bound to `collectors.collect_cpu` itself (same function) |
| **Classification** | **Always called, but never through a tool-based adapter** |

---

### `collect_tooling()` (lines 360–365)

| Attribute | Value |
|---|---|
| **Lines** | 360–365 |
| **Public/private** | Public |
| **Runtime paths** | A (service.py:180), C (doctor.py:117) |
| **HDO equivalent** | None — pure `shutil.which`, no subprocess |
| **Called via path A** | Always (no HDO slot exists) |
| **Called via path C** | Always (doctor ignores HDO entirely) |
| **HDO slot exists?** | No |
| **Classification** | **Always primary** — no HDO-based alternative exists |

---

## 3. Runtime Call Graph

```
bcs inventory (run_inventory)
  └─ collect_host_inventory(orchestrator=...)
       │
       ├─ orchestrator.discover()
       │    ├─ efi adapter (read_firmware_boot_configuration)  ← REAL ADAPTER
       │    ├─ storage adapter (read_storage_topology)          ← REAL ADAPTER
       │    ├─ secure_boot adapter (read_secure_boot_status)   ← REAL ADAPTER
       │    ├─ filesystem adapter (read_filesystem_usage)      ← REAL ADAPTER
       │    ├─ network adapter (read_network_interfaces)       ← REAL ADAPTER
       │    ├─ cpu: collect_cpu()              ← LEGACY (reused as HDO slot)
       │    └─ memory: collect_memory()        ← LEGACY (reused as HDO slot)
       │
       ├─ collect_identity()                  ← LEGACY, always, no HDO alternative
       ├─ collect_firmware()                  ← LEGACY, always, no HDO alternative
       ├─ collect_operating_system()          ← LEGACY, always, no HDO alternative
       ├─ collect_efi_system_partition()      ← LEGACY, always, no HDO alternative
       ├─ storage: _translate_storage_devices() if snapshot.storage_topology else collect_storage()  ← LEGACY FALLBACK
       ├─ usb_storage: collect_usb_storage()  ← LEGACY, always, no HDO alternative
       ├─ network: _translate_network_interfaces() if snapshot.network else collect_network()  ← LEGACY FALLBACK
       └─ collect_tooling()                   ← LEGACY, always, no HDO alternative


bcs doctor (run_doctor)
  └─ _ALL_CHECKS[check_name](runtime)
       │
       ├─ _check_firmware()
       │    └─ collect_firmware()             ← LEGACY, always, no orchestrator
       │
       ├─ _check_secure_boot()
       │    └─ collect_firmware()             ← LEGACY, always, same function called again
       │
       ├─ _check_storage()
       │    └─ collect_storage()              ← LEGACY, always, no orchestrator
       │
       ├─ _check_esp()
       │    └─ collect_efi_system_partition() ← LEGACY, always, no orchestrator
       │
       ├─ _check_usb_storage()
       │    └─ collect_usb_storage()          ← LEGACY, always, no orchestrator
       │
       ├─ _check_network()
       │    └─ collect_network()              ← LEGACY, always, no orchestrator
       │
       ├─ _check_tooling()
       │    └─ collect_tooling()              ← LEGACY, always, no orchestrator
       │
       ├─ _check_permissions()
       │    └─ (no collector — os.geteuid only)
       │
       └─ _check_config()
            └─ (no collector — config loader only)
```

---

## 4. Collector Dependency Graph

```
collect_firmware()
  ├── _read_secure_boot_state()
  └── _read_text() (via is_dir, not via this function's own code)

collect_storage()
  └── (stdlib: Path.glob)

collect_efi_system_partition()
  ├── _read_esp_mount()
  │    └── _read_text()
  ├── _parent_disk()
  ├── _partition_uuid()
  │    └── _read_text() (via os.path.realpath)
  └── _partition_usage()
       └── os.statvfs()

collect_usb_storage()
  ├── _is_usb_removable()
  │    └── _read_text()
  ├── _read_usb_storage_device()
  │    ├── _read_text()
  │    └── _find_mounted_partition()
  │         └── _read_text()
  └── (iteration: _SYS_BLOCK.iterdir)

collect_network()
  └── _read_text()

collect_identity()
  └── _primary_mac_address()
       └── _read_text()

collect_operating_system()
  └── _read_os_release_pretty_name()
       └── _read_text()

collect_memory()
  └── _parse_meminfo_kb_line()
       (uses _read_text() indirectly via its caller)

collect_cpu()
  └── _read_cpu_model()
       (uses _read_text() indirectly via its caller)

collect_tooling()
  └── shutil.which()

_root utility:
  _read_text() — called by 7 of 10 public collectors (directly or via private helpers)
```

---

## 5. Dead-Code Candidates

### Candidate D1: `_read_secure_boot_state()` (lines 86–92)

| Attribute | Value |
|---|---|
| **Always returns** | `SecureBootState.UNKNOWN` regardless of input |
| **Only caller** | `collect_firmware()` line 83 |
| **Logical behaviour** | **Dead by design** — the docstring at lines 89–91 explicitly marks it as a placeholder. The function body has no code path that could ever return a value other than `UNKNOWN` (the `efivars` check at line 87 just distinguishes `UNKNOWN` from `UNSUPPORTED`; neither branch reads an actual Secure Boot variable). |
| **Real implementation exists** | Yes — the Secure Boot adapter (`bcs.platform.adapters.secureboot`) correctly reads `mokutil --sb-state` and produces real `SecureBootStatus` data. But that data is held in `HostDiscoverySnapshot.secure_boot`, which no command consumes. |
| **Classification** | **Dead logic** — the function is called, but its output is always `UNKNOWN` |

### Candidate D2: `_read_text()` utility (lines 70–76)

| Attribute | Value |
|---|---|
| **Used by** | 7 of 10 public collectors (directly or via private helpers) |
| **Called at runtime** | Yes — extensively |
| **Dead?** | No — it is a shared utility, not dead code |
| **Classification** | **Not dead code** |

### Candidate D3: `collect_cpu()` via the HDO path

| Attribute | Value |
|---|---|
| **Called at runtime** | Yes — once per `bcs inventory`, via the HDO `cpu` slot which is bound to `collectors.collect_cpu` |
| **Dead?** | No — but the function is acting as an HDO slot, not as a "legacy collector" in the deprecation sense |
| **Classification** | **Not dead code** — will be permanently reused as an HDO callable |

### Candidate D4: `collect_memory()` via the HDO path

| Attribute | Value |
|---|---|
| **Same reasoning** | Identical to `collect_cpu()`. The HDO `memory` slot is bound to `collectors.collect_memory` |
| **Classification** | **Not dead code** — will be permanently reused as an HDO callable |

### Candidate D5: `collect_storage()` as fallback

| Attribute | Value |
|---|---|
| **Called on real hardware via inventory?** | Only if the Storage Adapter fails or the `storage` slot is unset — which it is not on any `bcs` invocation (the composition root always binds it). On a normal Ubuntu 24.04 system with `lsblk` available, `snapshot.storage_topology` is populated and the fallback is **never reached**. |
| **Called via doctor?** | Yes — `_check_storage()` always calls `collect_storage()` directly |
| **Doctor-blocked?** | Cannot remove until doctor migrates to HDO |
| **Classification** | **Fallback-only via inventory, primary via doctor** — not dead, but the inventory-side call path is effectively dead on real hardware |

### Candidate D6: `collect_network()` as fallback

| Attribute | Value |
|---|---|
| **Called on real hardware via inventory?** | Same reasoning as storage — only if the Network Adapter fails. On a normal Ubuntu 24.04 system with `ip` available, `snapshot.network` is populated and the fallback is **never reached**. |
| **Called via doctor?** | Yes — `_check_network()` always calls `collect_network()` directly |
| **Doctor-blocked?** | Cannot remove until doctor migrates to HDO |
| **Classification** | **Fallback-only via inventory, primary via doctor** — not dead, but the inventory-side call path is effectively dead on real hardware |

---

## 6. Fallback-Only Collectors (via Inventory)

These collectors are reached from `collect_host_inventory()` only when the
corresponding HDO slot produces `None` (adapter failure or unset slot).
On a normal system they are never reached from the inventory path.

| Collector | HDO Slot | Normal-path status | Fallback condition |
|---|---|---|---|
| `collect_storage()` | `storage` (Storage Adapter) | **Never reached** on real hardware | `snapshot.storage_topology is None` |
| `collect_network()` | `network` (Network Adapter) | **Never reached** on real hardware | `snapshot.network is None` |
| `collect_cpu()` | `cpu` (bound to collect_cpu itself) | **Always reached** (HDO slot IS the same function) | `snapshot.cpu is None` (never true) |
| `collect_memory()` | `memory` (bound to collect_memory itself) | **Always reached** (HDO slot IS the same function) | `snapshot.memory is None` (never true) |

**Key insight:** `collect_cpu()` and `collect_memory()` are special cases — the
HDO slot IS the same function, so they are always called regardless of whether
the fallback is exercised. They are not "replaced" by an adapter; they are
reused by one. The fallback branch in `service.py:156`/`:157` is unreachable
dead code (the HDO slot never returns `None` for these two).

**Key insight for storage and network:** on a normal system, these two collectors
are only reached from the doctor path. Removing them from `service.py` (making
the HDO translation unconditional) would have no visible effect on `bcs inventory`
output. But doctor still depends on them.

---

## 7. Collectors by Execution Status

| Collector | Inventory Path | Doctor Path | Status |
|---|---|---|---|
| `collect_firmware()` | Primary | Primary (2×) | **Always called, no HDO alternative** |
| `_read_secure_boot_state()` | Primary (via firmware) | Primary (via firmware) | **Dead logic inside live code** |
| `collect_storage()` | **Fallback only** | Primary | **Inventory fallback, doctor primary** |
| `collect_efi_system_partition()` | Primary | Primary | **Always called, no HDO alternative** |
| `collect_usb_storage()` | Primary | Primary | **Always called, no HDO alternative** |
| `collect_network()` | **Fallback only** | Primary | **Inventory fallback, doctor primary** |
| `collect_identity()` | Primary | **Never called** | **Inventory only, not doctor** |
| `collect_operating_system()` | Primary | **Never called** | **Inventory only, not doctor** |
| `collect_memory()` | Always (HDO slot is itself) | **Never called** | **Inventory only, reused as HDO slot** |
| `collect_cpu()` | Always (HDO slot is itself) | **Never called** | **Inventory only, reused as HDO slot** |
| `collect_tooling()` | Primary | Primary | **Always called, no HDO alternative** |

---

## 8. Remaining Blockers Before Complete Removal

For every legacy collector to be removable, each of these conditions must
be met:

### Blocker B1 — Doctor must consume the HDO pipeline

**Affects:** `collect_firmware()`, `collect_storage()`, `collect_efi_system_partition()`,
`collect_usb_storage()`, `collect_network()`, `collect_tooling()`

**Reason:** Doctor currently imports and calls 6 collectors directly at
`doctor.py:29-36`. Until `run_doctor()` passes `runtime.host_discovery_orchestrator`
through, and every `_check_*` function reads from the snapshot instead of
calling collectors, all 6 are required.

**Milestone:** Beta M2b (defined in `BETA_ROADMAP.md`).

### Blocker B2 — `HostInventory` schema must fold Discovery-domain fields

**Affects:** `collect_firmware()` (needs `secure_boot` + `firmware_boot_configuration` folded into `HostInventory`)

**Reason:** Even after doctor migrates, `collect_firmware()` is called from
`collect_host_inventory()` to populate `HostInventory.firmware`. There is no
HDO slot mapping to `FirmwareInfo`. Either:
- New `HostInventory` fields are added for `firmware_boot_configuration` and `secure_boot` (ADR-0008 amendment, M2c), or
- A translation function is added in `service.py` (Migration 2 in `LEGACY_COLLECTOR_MIGRATION_AUDIT.md`).

**Milestone:** Beta M2c + Migration 2.

### Blocker B3 — ESP business logic must exist

**Affects:** `collect_efi_system_partition()`

**Reason:** No HDO slot or business-logic function exists to derive the ESP
from `snapshot.storage_topology.devices[].partitions` by GPT PARTTYPE. A new
function (`_detect_esp()`) must be written.

**Milestone:** Migration 4 in `LEGACY_COLLECTOR_MIGRATION_AUDIT.md`.

### Blocker B4 — USB storage filter must exist

**Affects:** `collect_usb_storage()`

**Reason:** Same as B3 — no filter logic exists on the storage adapter's
`is_removable` field. A new function (`_detect_usb_devices()`) must be written.

**Milestone:** Migration 5 in `LEGACY_COLLECTOR_MIGRATION_AUDIT.md`.

### Blocker B5 — Identity must be sourced from adapters

**Affects:** `collect_identity()`

**Reason:** `dmi_product_uuid` must come from EFI adapter (if available) and
`primary_mac_address` from Network Adapter output. Both adapters exist; no
translation layer is written.

**Milestone:** Migration 6 in `LEGACY_COLLECTOR_MIGRATION_AUDIT.md`.

### Blocker B6 — HDO slots for OS and Tooling must be added

**Affects:** `collect_operating_system()`, `collect_tooling()`

**Reason:** Neither domain has an HDO slot. Adding them requires:
- New fields on `HostDiscoveryAdapters` / `HostDiscoverySnapshot` (`discovery/models.py`)
- New bindings in `app.py` composition root

No new adapter design needed — both are pure stdlib functions.

**Milestone:** Migration 7 in `LEGACY_COLLECTOR_MIGRATION_AUDIT.md`.

### Blocker B7 — `_read_secure_boot_state()` must be replaced

**Affects:** `_read_secure_boot_state()`

**Reason:** This function always returns `UNKNOWN`. Its replacement must either:
- Read the `SecureBoot-<GUID>` EFI variable's byte value, or
- Route through the Secure Boot adapter (preferred approach per Beta roadmap M4).

**Milestone:** Beta M4.

---

## 9. Summary: Code Status at a Glance

```
                   inventory   doctor
                   path        path
                   ─────────── ─────────
collect_firmware   PRIMARY     PRIMARY (2×)
collect_storage    FALLBACK    PRIMARY
collect_efi..      PRIMARY     PRIMARY
collect_usb..      PRIMARY     PRIMARY
collect_network    FALLBACK    PRIMARY
collect_identity   PRIMARY     —
collect_os         PRIMARY     —
collect_memory     HDO-REUSE   —
collect_cpu        HDO-REUSE   —
collect_tooling    PRIMARY     PRIMARY
                   ─────────── ─────────
                   10 called   6 called
```

- **0 collectors are completely unused** at runtime
- **1 function (`_read_secure_boot_state()`) is dead logic** inside a live caller
- **2 collectors are fallback-only** via the inventory path (storage, network)
- **2 collectors are HDO-reused** (cpu, memory — the HDO slot IS the legacy function)
- **4 collectors are always primary** with no HDO alternative (firmware, esp, usb, tooling)
- **2 collectors are inventory-only** (identity, os)
- **6 blockers** must be resolved before the legacy collectors can be removed from `service.py` and `doctor.py`
