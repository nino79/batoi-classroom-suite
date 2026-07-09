# Hardware Validation Matrix — Beta

Expected `bcs` behaviour across every supported validation environment. This matrix is checked during each Beta validation session and updated as findings accumulate.

See [BETA_VALIDATION_PLAN.md](BETA_VALIDATION_PLAN.md) for the validation workflow and [VM_VALIDATION.md](VM_VALIDATION.md) for the individual test cases.

## Legend

| Symbol | Meaning |
|---|---|
| ✅ | Check passes without warnings |
| ⚠️ WARN | Check produces a warning (non-fatal) |
| ❌ FAIL | Check produces a failure (expected on this configuration) |
| – | Not applicable / not tested |
| ? | Unknown — no data from this environment yet |

## Validation Matrix

| # | Environment | Storage | FW | SB | `bcs doctor` (expected) | `bcs inventory` | `bcs validate` | Expected Caveats | Observations |
|---|---|---|---|---|---|---|---|---|---|
| E01 | Ubuntu 24.04, VirtualBox 7.x | NVMe (virt) | UEFI | N/A | firmware: ✅, secure-boot: ❌ (SB unavailable in VBox), esp: ✅, storage: ✅, usb-storage: ✅, network: ✅, tooling: ❌ (no Clonezilla), permissions: ⚠️ (non-root), config: ⚠️ (no config path) | All 10 sections present. `storage` array populated with virtual NVMe device. `secureBoot` = `UNSUPPORTED`. `tooling` shows Clonezilla missing. | `default.yaml` exits 0 | `mokutil` not found → caveats entry. VirtualBox EFI provides minimal boot entries. | Reference environment for all Beta validation. [VM_FIRST_BOOT.md](VM_FIRST_BOOT.md) documents exact VM setup. |
| E02 | Ubuntu 24.04 (physical) | NVMe | UEFI | Disabled | firmware: ✅, secure-boot: ✅ (disabled), esp: ✅, storage: ✅, usb-storage: ✅ (if USB inserted), network: ✅, tooling: ❌ (no Clonezilla), permissions: ⚠️, config: ⚠️ | All 10 sections. `storage` array contains real NVMe devices. `secureBoot` = `DISABLED`. `storageTopology` adapter data collected but not surfaced (HDO not consumed). | `default.yaml` exits 0 | Real UEFI firmware produces richer `efibootmgr` output than VirtualBox. `mokutil` present and reports `disabled`. | Primary physical validation target. |
| E03 | Ubuntu 24.04 (physical) | NVMe | UEFI | Enabled | firmware: ✅, secure-boot: ✅ (enabled), esp: ✅, storage: ✅, usb-storage: ✅, network: ✅, tooling: ❌, permissions: ⚠️, config: ⚠️ | Same as E02. `secureBoot` = `ENABLED`. | `default.yaml` exits 0 | `mokutil --sb-state` reports `enabled`. No signing pipeline exists yet (Phase 5). | Validates that Secure Boot detection works without a signing requirement. |
| E04 | Ubuntu 24.04 (physical) | SATA SSD | UEFI | Either | firmware: ✅, secure-boot: depends, esp: ✅, storage: ⚠️ (no NVMe detected), usb-storage: ✅, network: ✅, tooling: ❌, permissions: ⚠️, config: ⚠️ | `storage` array populated with SATA device(s). No NVMe entries. `secureBoot` per environment. | `default.yaml` exits 0 | SPEC stipulates NVMe as primary (PLAT-005). SATA detection is best-effort. `bcs doctor` storage check does not fail on missing NVMe — it reports whatever is found. | Best-effort only. Not a supported target for v1.0 per PLAT-005. |
| E05 | Debian 12 | NVMe or SATA | UEFI | Either | firmware: ✅, secure-boot: depends, esp: ✅, storage: ✅, usb-storage: ✅, network: ✅, tooling: ❌, permissions: ⚠️, config: ⚠️ | All 10 sections. `operatingSystem` reports Debian 12. | `default.yaml` exits 0 | BCS targets LliureX 23 / Ubuntu 24.04 (PLAT-001/002). Debian is not a target but should install and run. Tooling check will report missing Clonezilla. | Informational — validates Python/CLI portability. No regression expected. |
| E06 | LliureX 23 (physical) | NVMe | UEFI | Either | firmware: ✅, secure-boot: depends, esp: ✅, storage: ✅, usb-storage: ✅, network: ✅, tooling: ✅ (Clonezilla present on LliureX), permissions: ⚠️, config: ⚠️ | All 10 sections. `operatingSystem` reports LliureX 23. `tooling` shows Clonezilla and Partclone present. | `default.yaml` exits 0 | This is the actual target platform. Tooling check passes because Clonezilla/Partclone are installed in LliureX by default. | Most representative environment. Run before declaring Beta complete. |
| E07 | Ubuntu 24.04 (USB SSD) | USB SSD | UEFI | Either | firmware: ✅, secure-boot: depends, esp: ✅, storage: ✅, usb-storage: ⚠️ (USB boot device may appear in usb-storage), network: ✅, tooling: ❌, permissions: ⚠️, config: ⚠️ | `storage` array may show the USB SSD. `usbStorage` may also list the boot device if it is removable. | `default.yaml` exits 0 | USB-attached boot media may appear in both `storage` and `usbStorage` depending on kernel classification. This is a known schema boundary ambiguity. | Informational — helps refine USB detection heuristics. |
| E08 | Ubuntu 24.04 (USB flash) | USB flash | UEFI | Either | firmware: ✅, secure-boot: depends, esp: ✅, storage: ✅, usb-storage: ⚠️ (flash drive reported), network: ✅, tooling: ❌, permissions: ⚠️, config: ⚠️ | `storage` array populated with flash device. `usbStorage` also lists it. | `default.yaml` exits 0 | Flash drives are slow: CLI performance (<5s) may be affected by storage adapter commands (`lsblk`, `blkid`). | Informational — validates CLI on low-performance storage. |

## Notes

- **Tooling check always fails on non-LliureX environments.** This is by design — Clonezilla and Partclone are only expected on LliureX systems. See [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md) and `bcs doctor`'s own documentation.
- **`bcs validate`** always uses the shipped `config/examples/default.yaml`. Results should be identical across all environments because validation is purely structural.
- **`bcs doctor` Secure Boot check** relies on the host `mokutil` binary. On VirtualBox (E01) it is absent → `CommandNotFoundError`, which is caught by the Host Discovery Orchestrator and reported as a caveat. On physical machines the tool is present and reports real state.
- **Storage arrays may be empty** in `bcs inventory` on certain configurations (see [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md)). This is a known collector limitation, not a hardware detection failure.
- Environments E04, E07, E08 are informational only — results inform future hardware support decisions but do not block Beta.

## Related Documents

- [BETA_VALIDATION_PLAN.md](BETA_VALIDATION_PLAN.md)
- [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md)
- [HARDWARE_MATRIX.md](HARDWARE_MATRIX.md) — the adapter-level hardware requirements
- [SPECIFICATION.md](../SPECIFICATION.md) — target platform requirements (PLAT-001 through PLAT-007)
