# Firmware Fixtures — UEFI Boot Configuration

Captured output for the **EFI Adapter** (`bcs.platform.adapters.efi`, see
[docs/EFI_ADAPTER.md](../../../../docs/EFI_ADAPTER.md)). General collection,
locale, anonymization, naming, and placeholder rules are in the
[corpus root README](../README.md) and are not restated here.

## Required Command Line

Exactly the invocation the adapter's accepted design specifies — the `-v`
flag and nothing else ([docs/EFI_ADAPTER.md § Adapter
Responsibilities](../../../../docs/EFI_ADAPTER.md#adapter-responsibilities)):

```
LC_ALL=C LANG=C efibootmgr -v > <fixture-name>.txt
```

Record the tool version (`efibootmgr -V`) in the inventory table below and
in the fixture's filename.

## Layout

Vendor subdirectories exist because UEFI NVRAM behaviour is known to vary
significantly by OEM ([docs/architecture/boot-manager.md § Open
Questions](../../../../docs/architecture/boot-manager.md#open-questions),
`BM-003`) — capturing the same scenario across the vendors actually found
in classroom hardware is exactly the observation this corpus exists to
support:

| Directory | Contents |
|---|---|
| `generic/` | Captures where the vendor is irrelevant to the scenario (VMs, any-vendor baselines). |
| `dell/`, `hp/`, `lenovo/` | Captures from real OEM classroom hardware, for vendor-specific quirks. Add further vendor directories as real hardware dictates — don't pre-create them speculatively. |

## Inventory

Every fixture (including placeholders) gets a row here. **All current
entries are zero-byte placeholders** — no real output has been captured
yet; see the root README's placeholder rules.

| File | Scenario | Status | Tool version | Captured on / from | Anonymized |
|---|---|---|---|---|---|
| `generic/efibootmgr_unknown_ubuntu-24.04_single-boot.txt` | Single Ubuntu boot entry, no BootNext | placeholder | — | — | — |
| `generic/efibootmgr_unknown_ubuntu-24.04_dual-boot-windows.txt` | Ubuntu + Windows Boot Manager dual boot | placeholder | — | — | — |
| `generic/efibootmgr_unknown_ubuntu-24.04_boot-next-set.txt` | One-time BootNext override set | placeholder | — | — | — |
| `dell/efibootmgr_unknown_lliurex-23_classroom-baseline.txt` | Baseline capture from a real Dell classroom machine | placeholder | — | — | — |
| `hp/efibootmgr_unknown_lliurex-23_classroom-baseline.txt` | Baseline capture from a real HP classroom machine | placeholder | — | — | — |
| `lenovo/efibootmgr_unknown_lliurex-23_classroom-baseline.txt` | Baseline capture from a real Lenovo classroom machine | placeholder | — | — | — |

The three `generic/` scenarios mirror the parser test plan in
[docs/EFI_ADAPTER.md § Testing Strategy](../../../../docs/EFI_ADAPTER.md#testing-strategy).
