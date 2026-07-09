# Hardware Support Matrix — `bcs` CLI (Phase 0)

This document records the hardware and software properties the `bcs` CLI — specifically the Platform Layer adapters and Host Inventory collectors — expects to encounter on a LliureX 23 classroom machine, as specified in [SPECIFICATION.md](../SPECIFICATION.md). All values are read-only: the CLI inspects and reports, it does not configure or modify hardware.

## Target Platform (Immutable)

Per [SPECIFICATION.md §1.3](../SPECIFICATION.md#13-target-platform):

| Property | Value |
|---|---|
| OS | LliureX 23 (based on Ubuntu 24.04 LTS) |
| Firmware | UEFI (no legacy BIOS support) |
| Primary storage | NVMe (no SATA/AHCI primary targets) |
| Deployment engine | Clonezilla |

## Adapter Requirements

### EFI Adapter (`bcs.platform.adapters.efi`)

| Requirement | Detail |
|---|---|
| Tool | `efibootmgr` (Ubuntu 24.04 package `efibootmgr`) |
| Firmware | UEFI 2.x+ |
| Locale | `LANG=C`/`LC_ALL=C` forced |
| Read-only | Never reads/writes NVRAM |
| Parses | Boot order, current boot entry, boot entries list |
| Sources | stdout of `efibootmgr -v` |

### Storage Adapter (`bcs.platform.adapters.storage`)

| Requirement | Detail |
|---|---|
| Tool chain | `lsblk` (util-linux), `blkid` (util-linux), `findmnt` (util-linux) |
| Storage | NVMe primary; SATA detected but not assumed primary |
| Partition table | GPT (not MBR) |
| Filesystems | vfat (ESP), ext4, btrfs (detected; others passed through) |
| Scope | Read-only topology: device tree, partition layout, mount points |
| Not inferred | Primary/system disk, installation target, boot disk |

### Secure Boot Adapter (`bcs.platform.adapters.secureboot`)

| Requirement | Detail |
|---|---|
| Tool | `mokutil` (Ubuntu 24.04 package `mokutil`) |
| Firmware | UEFI Secure Boot (SB/SETUP modes) |
| Locale | `LANG=C`/`LC_ALL=C` forced |
| States | `enabled`, `disabled`, `unsupported`, `unknown` |
| Sources | stdout of `mokutil --sb-state` |

### Filesystem Adapter (`bcs.platform.adapters.filesystem`)

| Requirement | Detail |
|---|---|
| Tool | `df` (coreutils) |
| Scope | Usage/capacity per mount point |
| Special handling | vfat inode reporting (`-` token → `None`), overmounting (duplicate targets preserved) |
| Not inferred | No "low space" warnings; raw bytes only |
| Sources | `df --output=source,fstype,itotal,iused,iavail,size,used,avail,target -B1 -a` |

### Network Adapter (`bcs.platform.adapters.network`)

| Requirement | Detail |
|---|---|
| Tool chain | `ip` (iproute2) |
| Status | Fully implemented as package; NOT yet wired into composition root |
| Current collector | `sysfs`-based `bcs.inventory.collectors.collect_network()` |
| Scope | Interface enumeration, MAC, link state, (future: `ip_addresses`) |

## Inventory Collectors (No Dedicated Adapter)

These fact areas use direct `sysfs`/`proc`/`DMI` reads rather than a Platform Layer adapter:

| Collector | Source | Facts |
|---|---|---|
| `collect_firmware()` | `/sys/firmware/efi`, DMI | UEFI presence, vendor, version |
| `collect_secure_boot()` | `/sys/firmware/efi/efivars/SecureBoot-*` | Secure Boot state (bool) |
| `collect_efi_system_partition()` | `/proc/mounts`, `/sys/block` | ESP mount, device, UUID, free space |
| `collect_cpu()` | `/proc/cpuinfo` | Architecture, model, cores |
| `collect_memory()` | `/proc/meminfo` | Total/available RAM |
| `collect_usb_storage()` | `/sys/block` + sysfs heuristics | Removable USB devices |
| `collect_identity()` | network sysfs + DMI | Primary MAC, DMI product UUID |
| `collect_operating_system()` | `/etc/os-release` | OS name, version, kernel |
| `collect_tooling()` | `shutil.which` | Tool presence (Clonezilla, partclone, etc.) |

## VM Compatibility

For demos and development on VirtualBox VMs:

| Feature | VirtualBox Support | Notes |
|---|---|---|
| UEFI | ✅ EFI enabled via VM settings | Must enable in VM config; not default |
| NVMe | ✅ NVMe controller | Must add NVMe controller (not SATA) |
| Secure Boot | ❌ VirtualBox EFI does not implement SB | Adapter returns `UNSUPPORTED` |
| `efibootmgr` | ✅ Works with VirtualBox EFI | Boot entries are minimal |
| `mokutil` | ❌ Tool absent; adapter returns `CommandNotFoundError` | Falls into caveats |
| Network | ✅ NAT or bridged | Facts are VM-specific |
| ESP | ✅ Created by Ubuntu installer | Usually `/dev/nvme0n1p1` on `/boot/efi` |

## Known Non-Goals

Per [SPECIFICATION.md §4](../SPECIFICATION.md#4-explicit-non-goals):

- Legacy BIOS firmware — not supported, not detected
- SATA/AHCI primary storage — detected but never treated as primary
- Non-NVMe boot devices — detected but not preferred
- ARM/other architectures — x86_64 only
- Non-Ubuntu/Debian distributions — LliureX/Ubuntu only
