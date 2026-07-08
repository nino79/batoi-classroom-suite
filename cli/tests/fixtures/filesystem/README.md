# Filesystem Fixtures — Disk Usage / Mount Points

Captured output for the **Filesystem Adapter** (`bcs.platform.adapters.filesystem`,
`df`-backed, see [docs/FILESYSTEM_ADAPTER.md](../../../../docs/FILESYSTEM_ADAPTER.md)).
General collection, locale, anonymization, naming, and placeholder rules are in the
[corpus root README](../README.md) and are not restated here.

## Required Command Line

Exactly the invocation the adapter's accepted design specifies — the
`--output=` columns, `-B1`, and `-a` flags and nothing else
([docs/FILESYSTEM_ADAPTER.md § Adapter
Responsibilities](../../../../docs/FILESYSTEM_ADAPTER.md#adapter-responsibilities)):

```
LC_ALL=C LANG=C df --output=source,fstype,itotal,iused,iavail,size,used,avail,target -B1 -a > <fixture-name>.txt
```

Record the tool version (`df --version`, first line) in the inventory table
below and in the fixture's filename.

> **`-a` includes pseudo-filesystems.** A real capture will contain `proc`,
> `sysfs`, `cgroup`-style entries. These are captured as-is, not trimmed
> out before saving — the fixture must reflect exactly what `df` produced.

## Layout

No vendor subdirectories, unlike `firmware/`. `df`'s output has no
firmware-vendor-specific variability — a flat `filesystem/*.txt` layout
mirrors `secureboot/`'s own precedent and rationale exactly. All fixtures
live directly under this directory.

## Inventory

Every fixture (including placeholders) gets a row here. **All current
entries are zero-byte placeholders** — no real output has been captured
yet; see the root README's placeholder rules.

| File | Scenario | Status | Tool version | Captured on / from | Anonymized |
|---|---|---|---|---|---|
| `df_unknown_ubuntu-24.04_typical-nvme-laptop.txt` | Root `ext4` + `/boot/efi` `vfat` + `-a`-visible pseudo-filesystems, moderate usage — the baseline case | placeholder | — | — | — |
| `df_unknown_ubuntu-24.04_vfat-reports-no-inodes.txt` | An entry with `-` for `itotal`/`iused`/`iavail`, exercising the `None`-inode parsing rule — realistic, since the ESP itself is `vfat` | placeholder | — | — | — |
| `df_unknown_ubuntu-24.04_mount-point-with-space.txt` | A `target` containing an embedded space, exercising the `maxsplit`-based column-splitting strategy | placeholder | — | — | — |
| `df_unknown_ubuntu-24.04_duplicate-target.txt` | Two lines reporting the same `target`, exercising the deliberate non-rejection of duplicates (mount stacking is a real, legitimate machine state) | placeholder | — | — | — |
| `df_unknown_ubuntu-24.04_unavailable-stdout.txt` | Partial failure: stdout containing every filesystem `df` could still read, paired with a non-empty stderr | placeholder | — | — | — |
| `df_unknown_ubuntu-24.04_unavailable-stderr.txt` | Stderr half of the partial-failure pair (exit code: TBD on capture) | placeholder | — | — (exit code: TBD on capture) | — |

These five scenarios mirror the parser test plan in
[docs/FILESYSTEM_ADAPTER.md § Fixtures
Strategy](../../../../docs/FILESYSTEM_ADAPTER.md#fixtures-strategy).
