# Unused Platform Adapters — Detection and Status

**Generated:** 2026-07-09
**Method:** Trace every adapter's data through the execution pipeline — from composition root (`app.py`) through `HostDiscoveryOrchestrator.discover()` to `collect_host_inventory()` to command output (`bcs inventory`, `bcs doctor`). An adapter is "consumed" when its output reaches a user-visible command result.

---

## Adapter Consumption Status

| Adapter | Produced by | Wired in Composition Root? | Invoked by Orchestrator? | Data Reaches CLI? | Status |
|---|---|---|---|---|---|
| **EFI** (`read_firmware_boot_configuration`) | `efibootmgr` subprocess | ✅ `app.py:215` (`efi` slot) | ✅ Yes | ❌ **No** | 🟡 **Dead output** — subprocess runs, data is discarded |
| **Storage** (`read_storage_topology`) | `lsblk` + `blkid` + `findmnt` subprocesses | ✅ `app.py:216` (`storage` slot) | ✅ Yes | ✅ `bcs inventory` via `_translate_storage_devices` (issue #70) | ✅ **Consumed** |
| **Secure Boot** (`read_secure_boot_status`) | `mokutil` subprocess | ✅ `app.py:217` (`secure_boot` slot) | ✅ Yes | ✅ Partial — `state` reaches `bcs inventory` via `_translate_secure_boot_state` (Beta M4); `setup_mode`/`raw_text` discarded | 🟡 **Partially consumed** — `state` consumed, richer data discarded |
| **Filesystem** (`read_filesystem_usage`) | `df` subprocess | ✅ `app.py:218` (`filesystem` slot) | ✅ Yes | ❌ **No** | 🔴 **Dead output + wasted subprocess** — `df` runs, data is discarded entirely |
| **Network** (`read_network_interfaces`) | `ip -json addr show` subprocess | ✅ `app.py:219` (`network` slot) | ✅ Yes | ✅ `bcs inventory` via `_translate_network_interfaces` (Beta M3) | ✅ **Consumed** |

---

## Detailed Analysis

### EFI Adapter (`read_firmware_boot_configuration`)

| Attribute | Value |
|---|---|
| **Adapter package** | `cli/src/bcs/platform/adapters/efi/` (models, parser, errors, adapter — all implemented) |
| **Composition root** | `app.py:215` — `functools.partial(read_firmware_boot_configuration, runner=command_runner)` |
| **HDO slot** | `HostDiscoverySnapshot.firmware_boot_configuration` |
| **Orchestrator calls it?** | Yes — during `orchestrator.discover()` |
| **Data consumed by?** | **None** — no `HostInventory` field maps to `FirmwareBootConfiguration` |
| **Why not consumed** | `HostInventory` has no `firmwareBootConfiguration` field. Adding one requires an ADR-0008 amendment (ADR-0011 Decision point 6) |
| **Wasted work** | `efibootmgr` subprocess runs on every `bcs inventory` and every `bcs doctor` invocation; its output (~10-30 lines of UEFI boot entries) is parsed into `FirmwareBootConfiguration` and then discarded |
| **What milestone consumes it** | Not scheduled — deferred until ADR-0008 amendment is accepted |

### Filesystem Adapter (`read_filesystem_usage`)

| Attribute | Value |
|---|---|
| **Adapter package** | `cli/src/bcs/platform/adapters/filesystem/` (models, parser, errors, adapter — all implemented) |
| **Composition root** | `app.py:218` — `functools.partial(read_filesystem_usage, runner=command_runner)` |
| **HDO slot** | `HostDiscoverySnapshot.filesystem` |
| **Orchestrator calls it?** | Yes — during `orchestrator.discover()` |
| **Data consumed by?** | **None** — no `HostInventory` field maps to `FilesystemUsageReport` |
| **Why not consumed** | `HostInventory` has no `filesystemUsage` field. Adding one requires a schema change |
| **Wasted work** | `df` subprocess runs on every `bcs inventory` and every `bcs doctor` invocation; its output (full mount table) is parsed and then discarded |
| **What milestone consumes it** | Not scheduled — post-Beta enhancement |

### Secure Boot Adapter (`read_secure_boot_status`) — Partial Consumption

| Attribute | Value |
|---|---|
| **Consumed fields** | `state` → `HostInventory.firmware.secureBoot` via `_translate_secure_boot_state()` (service.py:152-165) |
| **Unconsumed fields** | `setup_mode` (`bool \| None`), `raw_text` (`str`) |
| **Why not fully consumed** | `HostInventory.FirmwareInfo` has no `setupMode` or `rawText` fields. Adding them requires a schema change |
| **Impact** | Low — `setup_mode` is informative but not critical for Beta; `raw_text` is debug-only |
| **What milestone consumes the rest** | Not scheduled — post-Beta enhancement |

---

## Caveats (`HostDiscoverySnapshot.caveats`)

| Attribute | Value |
|---|---|
| **Produced by** | `HostDiscoveryOrchestrator.discover()` — collects `{domain}: {ExceptionType}: {message}` strings from any adapter that raised a `PlatformError` |
| **Consumed by?** | **None** — `caveats` is never read by any code path |
| **Why not consumed** | No CLI command surfaces orchestrator errors to the user |
| **Impact** | Medium — adapter failures are silently swallowed; the user sees fallback data (or missing data) with no indication that an adapter failed |
| **What milestone consumes it** | Not scheduled — requires CLI design for error surfacing |

---

## Summary

| Category | Count | Items |
|---|---|---|
| **Fully consumed** | 2 | Storage adapter, Network adapter |
| **Partially consumed** | 1 | Secure Boot adapter (`state` reaches CLI; `setup_mode`/`raw_text` discarded) |
| **Produced but discarded** | 2 | EFI adapter (`FirmwareBootConfiguration`), Filesystem adapter (`FilesystemUsageReport`) |
| **Produced but unexposed** | 1 | `caveats` (orchestrator error aggregation — never shown to user) |

---

## Recommendations

1. **EFI adapter — lowest priority to consume.** The `FirmwareBootConfiguration` model is rich (boot entries, boot order, timeout) but its utility is limited until the future Boot Manager component needs it. No Beta milestone should block on this.
2. **Filesystem adapter — wasted subprocess.** Since `df` output is produced and discarded on every CLI invocation, consider either (a) adding a `HostInventory.filesystemUsage` field, or (b) removing the `filesystem` slot from the composition root until a consumer exists. Option (b) is a one-line change in `app.py`.
3. **Caveats — should be surfaced.** The orchestrator already collects adapter failure information but never shows it to the user. A simple "X adapter(s) unavailable, using fallback data" line in `bcs inventory`/`bcs doctor` output would be valuable.
