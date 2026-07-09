# Hardware Validation Toolkit

**Purpose:** Reusable Bash scripts for capturing, comparing, and summarizing hardware topology during Beta validation on physical classroom computers.

The toolkit produces structured JSON captures with a stable schema, human-readable Markdown summaries, and aggregated Beta validation reports. It requires no production code modifications, no Python, and no elevated privileges for most operations.

## Directory Layout

```
scripts/hardware-validation/
├── _shared.sh              # Shared library (JSON helpers, logging, tool detection)
├── capture-system.sh       # Kernel, distribution, CPU, memory, DMI, hypervisor, tools
├── capture-storage.sh      # Block devices, partitions, filesystems, mountpoints
├── capture-network.sh      # Interfaces, MAC, state, MTU, IPv4/IPv6 addresses
├── capture-firmware.sh     # UEFI mode, Secure Boot, boot entries, DMI firmware
├── capture-usb.sh          # USB controllers, devices, removable storage
├── capture-all.sh          # Orchestrator — runs every capture, writes summary
├── compare.sh              # Compare two captures, generate diff report
└── summarize.sh            # Aggregate multiple captures into Beta validation report
```

## Capture Format

Each capture-all.sh run produces a directory:

```
hardware-validation/<machine-name>/<timestamp>/
├── system.json
├── storage.json
├── network.json
├── firmware.json
├── usb.json
├── system-summary.md
├── storage-summary.md
├── network-summary.md
├── firmware-summary.md
├── usb-summary.md
└── summary.md
```

### JSON Schema Stability

Each JSON file follows a documented schema designed to remain stable across toolkit versions. Fields are additive only — a future version may add new keys but will never rename or remove existing ones.

#### system.json

```json
{
  "timestamp": "2026-07-09T12:00:00+02:00",
  "machine_name": "hostname",
  "kernel": "Linux hostname 6.8.0-31-generic ...",
  "distribution": {
    "id": "ubuntu",
    "version": "24.04",
    "pretty_name": "Ubuntu 24.04 LTS"
  },
  "cpu": {
    "model": "Intel(R) Core(TM) i5-10400 CPU @ 2.90GHz",
    "cores": 6,
    "threads": 12,
    "architecture": "x86_64"
  },
  "memory": {
    "total_mib": 16000,
    "available_mib": 8000
  },
  "dmi": {
    "product_name": "OptiPlex 7080",
    "product_uuid": "4c4c4544...",
    "vendor": "Dell Inc.",
    "bios_version": "1.14.0"
  },
  "hypervisor": "none",
  "tools": {
    "efibootmgr": "18",
    "mokutil": "0.6.0",
    "lsblk": "2.40.0",
    ...
  }
}
```

#### storage.json

```json
{
  "timestamp": "...",
  "machine_name": "...",
  "devices": [
    {
      "name": "nvme0n1",
      "model": "Samsung SSD 980 PRO 1TB",
      "size": 1000204886016,
      "type": "disk",
      "rota": false,
      "rm": false,
      "children": [
        {
          "name": "nvme0n1p1",
          "size": 536870912,
          "type": "part",
          "fstype": "vfat",
          "mountpoint": "/boot/efi",
          "uuid": "ABCD-1234"
        }
      ]
    }
  ]
}
```

#### network.json

```json
{
  "timestamp": "...",
  "machine_name": "...",
  "interfaces": [
    {
      "name": "enp0s3",
      "mac": "08:00:27:ab:cd:ef",
      "state": "up",
      "mtu": 1500,
      "speed": null,
      "ipv4": ["10.0.2.15/24"],
      "ipv6": ["fe80::a00:27ff:feab:cdef/64"]
    }
  ]
}
```

#### firmware.json

```json
{
  "timestamp": "...",
  "machine_name": "...",
  "uefi": true,
  "secure_boot": "disabled",
  "boot_entries": [
    {"number": "0000", "label": "ubuntu", "active": true},
    {"number": "0001", "label": "UEFI: USB", "active": true}
  ],
  "boot_order": ["0000", "0001"],
  "dmi": {
    "bios_vendor": "American Megatrends Inc.",
    "bios_version": "1.14.0",
    "bios_date": "03/17/2023",
    ...
  }
}
```

#### usb.json

```json
{
  "timestamp": "...",
  "machine_name": "...",
  "usb": {
    "controllers": [...],
    "devices": [...],
    "removable_storage": [...]
  }
}
```

## Workflow

### 1. Capture a single machine

```bash
# From repository root
./scripts/hardware-validation/capture-all.sh

# Custom output directory
./scripts/hardware-validation/capture-all.sh --dir /tmp/my-capture

# Human-readable only (no JSON)
./scripts/hardware-validation/capture-all.sh --human-only
```

This creates a `hardware-validation/<hostname>/<timestamp>/` directory with all capture files.

### 2. Run individual captures

```bash
# Capture only system data
./scripts/hardware-validation/capture-system.sh

# Capture with output directory
./scripts/hardware-validation/capture-storage.sh --dir /tmp/capture

# Human-readable only
./scripts/hardware-validation/capture-network.sh --human

# Capture firmware with DMI and Secure Boot
./scripts/hardware-validation/capture-firmware.sh

# Capture USB topology
./scripts/hardware-validation/capture-usb.sh
```

### 3. Compare two captures

```bash
# Compare two capture directories
./scripts/hardware-validation/compare.sh hardware-validation/machine-a/2026-07-09T12-00-00/ hardware-validation/machine-b/2026-07-09T14-00-00/

# Write comparison to file
./scripts/hardware-validation/compare.sh left-dir/ right-dir/ --output comparison.md

# Verbose output
./scripts/hardware-validation/compare.sh left-dir/ right-dir/ --verbose
```

### 4. Generate Beta validation report

```bash
# Summarize multiple captures by directory
./scripts/hardware-validation/summarize.sh --dir hardware-validation/

# Summarize specific captures
./scripts/hardware-validation/summarize.sh capture1/ capture2/ capture3/

# Write to file
./scripts/hardware-validation/summarize.sh --dir captures/ --output beta-report.md
```

## Example Commands

### Full validation cycle on a classroom machine

```bash
cd /path/to/batoi-classroom-suite

# 1. Capture
./scripts/hardware-validation/capture-all.sh

# 2. Run bcs validation
bcs validate config/examples/default.yaml
bcs doctor
bcs inventory --output json

# 3. Archive
./scripts/collect-artifacts.sh

# 4. (On central machine) collect USB drive with captures
# 5. Compare against baseline
./scripts/hardware-validation/compare.sh baseline/ new-capture/

# 6. Generate validation report
./scripts/hardware-validation/summarize.sh --dir hardware-validation/ --output beta-report.md
```

### Comparing firmware across identical machines

```bash
# Check that all classroom machines have the same firmware config
for machine in hardware-validation/*/; do
  echo "=== $(basename $machine) ==="
  cat "${machine}"/*/firmware.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'UEFI: {d[\"uefi\"]}, SB: {d[\"secure_boot\"]}, Boot: {len(d.get(\"boot_entries\",[]))} entries')"
done
```

## Script Reference

### `capture-all.sh`

| Option | Description |
|---|---|
| `--dir <path>` | Output directory (default: `hardware-validation/<hostname>/<timestamp>/`) |
| `--human-only` | Generate only Markdown summaries, no JSON |

### `capture-system.sh`

| Option | Description |
|---|---|
| `--dir <path>` | Output directory |
| `--human` | Human-readable Markdown to stdout only |

**Required tools:** none (stdlib reads only; `python3` enhances parsing).  
**Optional tools:** `nproc` (thread count), `dmidecode` (richer DMI).

### `capture-storage.sh`

| Option | Description |
|---|---|
| `--dir <path>` | Output directory |
| `--human` | Human-readable Markdown to stdout only |

**Required tools:** `lsblk` (from `util-linux`).  
**Optional tools:** `python3` (table formatting).

### `capture-network.sh`

| Option | Description |
|---|---|
| `--dir <path>` | Output directory |
| `--human` | Human-readable Markdown to stdout only |

**Required tools:** `ip` from `iproute2` (falls back to `/sys/class/net` without IP addresses).  
**Optional tools:** `python3` (IP address parsing).

### `capture-firmware.sh`

| Option | Description |
|---|---|
| `--dir <path>` | Output directory |
| `--human` | Human-readable Markdown to stdout only |

**Required tools:** none (UEFI detection via `/sys/firmware/efi`).  
**Optional tools:** `efibootmgr` (boot entries), `mokutil` (Secure Boot), `dmidecode` (DMI), `python3` (parsing). Script works with any subset.

### `capture-usb.sh`

| Option | Description |
|---|---|
| `--dir <path>` | Output directory |
| `--human` | Human-readable Markdown to stdout only |

**Required tools:** `lsusb` from `usbutils` (falls back to `/sys/bus/usb/devices/`).  
**Optional tools:** `python3` (parsing and device classification).

### `compare.sh`

| Option | Description |
|---|---|
| `left-dir` | First capture directory |
| `right-dir` | Second capture directory |
| `--output <file>` | Write report to file (default: stdout) |
| `--verbose` | Include more detail in diff output |

**Exit codes:**

| Code | Meaning |
|---|---|
| 0 | Comparison generated with differences |
| 1 | Missing directory or required files |
| 2 | No differences found |

### `summarize.sh`

| Option | Description |
|---|---|
| `--dir <path>` | Scan directory for capture subdirectories |
| `--output <file>` | Write report to file (default: stdout) |
| Capture directories | One or more capture directories as positional arguments |

## Example Output

### Comparison report snippet

```markdown
# Hardware Validation Comparison

**Compared:** classroom-pc-01 (left) vs classroom-pc-02 (right)

## Firmware

- **UEFI mode:** unchanged (true)
- **Secure Boot:** CHANGED
  - Left:  "disabled"
  - Right: "enabled"
- **Boot entries:** 1 difference(s)
  - boot_entries[0].label: "ubuntu" vs "Ubuntu"

## Storage

- **Devices:** 2 difference(s)
  - devices[0].model: "Samsung SSD 980 PRO 1TB" vs "WD Black SN850"
  - devices[0].size: 1000204886016 vs 1000202273280
```

### Beta validation report snippet

```markdown
# Beta Validation Report

**Machines validated:** 3

## Executive Summary

| Metric | Value |
|---|---|
| Total machines | 3 |
| UEFI firmware | 3 |
| Secure Boot enabled | 1 |
| NVMe storage | 3 |

## Hardware Matrix

| Machine | OS | CPU | Memory | UEFI | Secure Boot |
|---|---|---|---|---|---|
| pc-01 | Ubuntu 24.04 | i5-10400 | 16 GiB | ✅ | ✅ |
| pc-02 | Ubuntu 24.04 | i7-10700 | 32 GiB | ✅ | 🔒 |
| pc-03 | LliureX 23 | i5-10400 | 8 GiB | ✅ | ✅ |
```

## Future Extension Points

1. **Hardware database integration** — import captures into a SQLite database for historical trend analysis across validation rounds.
2. **CI artifact ingestion** — the `compare.sh` exit code 0/2 enables gating CI pipelines on hardware regressions.
3. **Golden baseline** — capture a reference machine and compare all subsequent captures against it.
4. **Performance benchmarks** — extend `capture-storage.sh` with `fio` or `dd` benchmarks, `capture-network.sh` with `iperf3` throughput test.
5. **Anomaly detection** — statistical comparison across N identical captures to flag outliers (e.g., a machine with degraded storage or network).
6. **HTML report generation** — convert Markdown reports to HTML with collapsible diffs and charts.
7. **Inventory merge** — combine hardware captures with `bcs inventory --output json` for a unified machine profile.
