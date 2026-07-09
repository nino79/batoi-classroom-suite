# VM Demo Guide — Running `bcs` on a Fresh Ubuntu 24.04 VM

This guide walks through setting up a VirtualBox VM that mimics a LliureX 23 classroom machine (UEFI, NVMe), installing the `bcs` CLI, and running every working command.

## Prerequisites

- **VirtualBox 7.x** with Extension Pack (for UEFI/NVMe support)
- **Ubuntu 24.04 LTS Server ISO** (`ubuntu-24.04-live-server-amd64.iso`)
- **4 GB RAM, 2 CPU cores, 50 GB virtual disk** (NVMe controller)
- **Network:** NAT (for `apt` access during setup only)

## VM Creation (VirtualBox)

| Setting | Value |
|---|---|
| Type | Linux |
| Version | Ubuntu 24.04 LTS (64-bit) |
| RAM | 4096 MB |
| CPUs | 2 |
| Storage Controller | NVMe (not SATA) |
| Disk | 50 GB dynamically allocated |
| EFI | Enable EFI (not BIOS) |
| Network | NAT (default) |

### CLI Setup

```bash
VBoxManage createvm --name "bcs-demo" --ostype Ubuntu24_64 --register
VBoxManage modifyvm "bcs-demo" --memory 4096 --cpus 2 --firmware efi
VBoxManage storagectl "bcs-demo" --name "NVMe" --add nvme --controller NVMe
VBoxManage storageattach "bcs-demo" --storagectl "NVMe" --port 0 --device 0 --type hdd \
  --medium "$HOME/VMs/bcs-demo.vdi" --mtype normal
VBoxManage modifyvm "bcs-demo" --nic1 nat
```

## OS Installation

1. Boot the ISO and select **Try or Install Ubuntu Server**
2. Choose language, keyboard, and network defaults (DHCP via NAT)
3. **Configure storage:** use the whole NVMe disk with default partition layout (an ESP will be created automatically)
4. Set a memorable username/password (e.g. `tech`/`bcsdemo`)
5. Install OpenSSH server when prompted
6. Reboot, remove the ISO

## BCS Setup

Run these commands **exactly once** after first boot:

```bash
# 1. System dependencies
sudo apt update && sudo apt install -y git python3-venv

# 2. Clone
git clone https://github.com/nino79/batoi-classroom-suite.git
cd batoi-classroom-suite/cli

# 3. Virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 4. Install bcs in dev mode
pip install -e ".[dev]"

# 5. Verify
bcs --help
bcs version
```

## Demo Commands

All commands assume the venv is active (`source .venv/bin/activate`) and the working directory is `cli/`.

### `bcs --help`

```bash
bcs --help
```

Expected: full command tree — `doctor`, `inventory`, `validate`, `version`, and the seven stubs (`build`, `install`, `deploy`, `backup`, `restore`, `update`, `config`).

### `bcs version`

```bash
bcs version
```

Expected: CLI version, commit, build date, supported config API versions.

### `bcs validate`

```bash
bcs validate ../config/examples/default.yaml
```

Expected: exit 0, prints validation result. If a config uses optional fields this machine doesn't satisfy, those appear as warnings.

### `bcs inventory`

```bash
bcs inventory
bcs inventory --output json
```

Expected: 10-section host snapshot (identity, firmware, OS, CPU, memory, storage, network, ESP, USB storage, tooling). JSON variant is parseable (`jq .`).

### `bcs doctor`

```bash
bcs doctor
```

Expected: per-check pass/fail/warn for `firmware`, `storage`, `network`, `tooling`, `config`, `permissions`, `esp`, `usb-storage`. A fresh VM will likely warn on `tooling` (Clonezilla not found) — that is by design.

### Stub Commands

```bash
bcs build --help
bcs install --help
bcs deploy --help
bcs backup --help
bcs restore --help
bcs update --help
bcs config --help
```

Each shows its help text and exits 0. Running without `--help` prints "not implemented in this phase."

## What NOT to Expect

- **Boot Manager, Builder, Deploy** — none exist yet; this is Phase 0
- **Real hardware detection** — the VM virtualises UEFI/NVMe, so adapter output is synthetic but structurally valid
- **Zero warnings** — `bcs doctor` warns about missing Clonezilla, which is expected on a non-LliureX machine

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| `bcs: command not found` | venv not activated | `source .venv/bin/activate` |
| `python3: module venv not found` | `python3-venv` not installed | `sudo apt install python3-venv` |
| `externally-managed-environment` error | `pip install` outside venv | Recreate with fresh venv |
| `bcs doctor` shows no EFI facts | VM booted in BIOS mode | Recreate VM with EFI enabled |
