# Secure Boot Fixtures — Firmware Secure Boot State

Captured output for the **Secure Boot Adapter** (`bcs.platform.adapters.secureboot`,
see [docs/SECURE_BOOT_ADAPTER.md](../../../../docs/SECURE_BOOT_ADAPTER.md)).
General collection, locale, anonymization, naming, and placeholder rules
are in the [corpus root README](../README.md) and are not restated here.

## Required Command Line

Exactly the invocation the adapter's accepted design specifies — the
`--sb-state` flag and nothing else ([docs/SECURE_BOOT_ADAPTER.md § Adapter
Responsibilities](../../../../docs/SECURE_BOOT_ADAPTER.md#adapter-responsibilities)):

```
LC_ALL=C LANG=C mokutil --sb-state > <fixture-name>.txt
```

Record the tool version (`mokutil --version`) in the inventory table below
and in the fixture's filename.

## Layout

No vendor subdirectories, unlike `firmware/`. `mokutil --sb-state` reads a
standardized UEFI variable via a generic Linux userspace tool, not
firmware-vendor-specific device-path text the way `efibootmgr`'s boot
entries are — a deliberate difference from `firmware/`'s layout, not an
oversight. All fixtures live directly under this directory.

## Inventory

Every fixture (including placeholders) gets a row here. **All current
entries are zero-byte placeholders** — no real output has been captured
yet; see the root README's placeholder rules.

| File | Scenario | Status | Tool version | Captured on / from | Anonymized |
|---|---|---|---|---|---|
| `mokutil_unknown_ubuntu-24.04_enabled.txt` | `SecureBoot enabled`, `SetupMode disabled` | placeholder | — | — | — |
| `mokutil_unknown_ubuntu-24.04_disabled.txt` | `SecureBoot disabled` | placeholder | — | — | — |
| `mokutil_unknown_ubuntu-24.04_setup-mode.txt` | `SecureBoot enabled`, `SetupMode enabled` — a distinct, security-relevant combination | placeholder | — | — | — |
| `mokutil_unknown_ubuntu-24.04_no-setup-mode-line.txt` | Only a `SecureBoot` line — covers `mokutil` versions/builds that don't report Setup Mode at all | placeholder | — | — | — |
| `mokutil_unknown_ubuntu-24.04_unavailable-stderr.txt` | Non-UEFI / unavailable case (stderr only, non-zero exit) | placeholder | — | — (exit code: TBD on capture) | — |

These scenarios mirror the parser/adapter test plan in
[docs/SECURE_BOOT_ADAPTER.md § Testing Strategy](../../../../docs/SECURE_BOOT_ADAPTER.md#testing-strategy).
