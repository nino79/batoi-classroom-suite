# Collector Call Graph — Every `collect_*` Invocation in Production Code

**Generated:** 2026-07-09
**Method:** Grep of `cli/src/bcs/` for every call to `collect_*` (excluding the definitions themselves and test files). Each call site is classified by whether it should disappear, stay, or transition.

---

## Production Call Sites

### `cli/src/bcs/inventory/service.py` — `collect_host_inventory()`

| Call | Line | Context | Fallback? | Must Disappear? | Rationale |
|---|---|---|---|---|---|
| `collectors.collect_firmware()` | 176 | Always called, stores result for conditional override | No (override, not fallback) | **Will stay** — `uefi`/`vendor`/`version` have no adapter equivalent; only `secure_boot` is overridden |
| `collectors.collect_cpu()` | 178 | No-orchestrator path | N/A (primary) | **Will stay** — pure Python, reused as HDO slot |
| `collectors.collect_memory()` | 179 | No-orchestrator path | N/A (primary) | **Will stay** — pure Python, reused as HDO slot |
| `collectors.collect_network()` | 180 | No-orchestrator path | N/A (primary in no-orch) | **Will stay** — needed for no-orchestrator fallback |
| `collectors.collect_storage()` | 181 | No-orchestrator path | N/A (primary in no-orch) | **Will stay** — needed for no-orchestrator fallback |
| `collectors.collect_cpu()` | 184 | Orchestrator path, fallback when `snapshot.cpu is None` | ✅ Yes | **Should disappear** — unreachable on healthy systems (HDO slot always populated) |
| `collectors.collect_memory()` | 185 | Orchestrator path, fallback when `snapshot.memory is None` | ✅ Yes | **Should disappear** — unreachable on healthy systems |
| `collectors.collect_storage()` | 189 | Orchestrator path, fallback when `snapshot.storage_topology is None` | ✅ Yes | **Should disappear** — unreachable on healthy systems |
| `collectors.collect_network()` | 194 | Orchestrator path, fallback when `snapshot.network is None` | ✅ Yes | **Should disappear** — unreachable on healthy systems |
| `collectors.collect_identity()` | 203 | Always called | No | **Will stay** — no adapter equivalent (could be derived from EFI + Network adapters, speculative) |
| `collectors.collect_operating_system()` | 205 | Always called | No | **Will stay** — pure Python, no adapter planned |
| `collectors.collect_efi_system_partition()` | 208 | Always called | No | **Should be replaced** — derivable from Storage adapter data |
| `collectors.collect_usb_storage()` | 210 | Always called | No | **Should be replaced** — derivable from Storage adapter data |
| `collectors.collect_tooling()` | 212 | Always called | No | **Will stay** — pure Python, no adapter planned |

### `cli/src/bcs/commands/doctor.py` — `_check_*` functions

| Call | Line | Function | Context | Must Disappear? | Rationale |
|---|---|---|---|---|---|
| `collect_firmware()` | 93 | `_check_firmware` | Always called, checks `uefi` flag | **Will stay** — no adapter for `uefi` boolean; cheap directory check |
| `collect_firmware()` | 113 | `_check_secure_boot` | Always called (UEFI gate before adapter call) | **Should stay** — cheap guard before expensive adapter call; runs `read_firmware_boot_configuration`'s equivalent logic without a subprocess |
| `collect_storage()` | 156 | `_check_storage` | Fallback when `read_storage_topology` raises `PlatformError` | **Should stay** — defensive fallback when adapter is unavailable |
| `collect_efi_system_partition()` | 166 | `_check_esp` | Always called | **Should be replaced** — derivable from Storage adapter data |
| `collect_usb_storage()` | 175 | `_check_usb_storage` | Always called | **Should be replaced** — derivable from Storage adapter data |
| `collect_network()` | 197 | `_check_network` | Fallback when `read_network_interfaces` raises `PlatformError` | **Should stay** — defensive fallback when adapter is unavailable |
| `collect_tooling()` | 219 | `_check_tooling` | Always called | **Will stay** — pure Python, no adapter planned |

### `cli/src/bcs/app.py` — Composition Root

| Call | Line | Context | Must Disappear? | Rationale |
|---|---|---|---|---|
| `collectors.collect_cpu` | 220 | Passed as reference for HDO `cpu` slot binding | **Will stay** — reused as HDO slot, pure Python |
| `collectors.collect_memory` | 221 | Passed as reference for HDO `memory` slot binding | **Will stay** — reused as HDO slot, pure Python |

---

## Test Call Sites (informational — no changes planned)

### `cli/tests/test_inventory_collectors.py`

| Call | Line | Classification |
|---|---|---|
| `collectors.collect_firmware()` | 19, 31, 45 | Unit tests for the function itself — must stay |
| `collectors.collect_storage()` | 57, 68 | Unit tests — must stay |
| `collectors.collect_efi_system_partition()` | 83, 92, 127, 176 | Unit tests — must stay |
| `collectors.collect_usb_storage()` | 193, 223, 263, 282 | Unit tests — must stay |
| `collectors.collect_network()` | 304, 314 | Unit tests — must stay |
| `collectors.collect_identity()` | 337, 348 | Unit tests — must stay |
| `collectors.collect_operating_system()` | 364, 373 | Unit tests — must stay |
| `collectors.collect_memory()` | 381, 393 | Unit tests — must stay |
| `collectors.collect_cpu()` | 402, 414 | Unit tests — must stay |
| `collectors.collect_tooling()` | 428 | Unit tests — must stay |

### `cli/tests/test_inventory_service.py`

All calls to `collect_*` here are patched via `monkeypatch.setattr`. They test `collect_host_inventory()`'s orchestrator/fallback logic — these should stay as long as the fallback paths exist.

### `cli/tests/test_host_discovery_pipeline.py`

| Call | Line | Classification |
|---|---|---|
| `collectors.collect_cpu` | 117 | HDO slot reference in end-to-end test — must stay |
| `collectors.collect_memory` | 118 | HDO slot reference — must stay |

### `cli/tests/test_host_discovery_wiring.py`

| Call | Line | Classification |
|---|---|---|
| `collectors.collect_cpu` | 179 | Composition root wiring test — must stay |
| `collectors.collect_memory` | 180 | Composition root wiring test — must stay |

---

## Summary

| Fate | Count | Collectors |
|---|---|---|
| **Will stay** (pure Python, no replacement) | 5 | `collect_firmware()` (UEFI gate), `collect_identity()`, `collect_operating_system()`, `collect_tooling()`, `collect_cpu()`, `collect_memory()` |
| **Will stay as defensive fallback** | 3 | `collect_storage()` (doctor), `collect_network()` (doctor), `collect_storage()`/`collect_network()` (inventory no-orch path) |
| **Should be replaced** (derivable from adapter data) | 2 | `collect_efi_system_partition()`, `collect_usb_storage()` |
| **Should disappear** (fallbacks unreachable on healthy systems) | 4 | `collect_cpu()`/`collect_memory()`/`collect_storage()`/`collect_network()` fallbacks in `service.py` orchestrator path |
