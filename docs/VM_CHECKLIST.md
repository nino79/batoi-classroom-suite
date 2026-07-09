# VM Demo Checklist — `bcs` on Ubuntu 24.04

Use this checklist to verify every working command before and during the demo.

## Pre-Demo Setup

- [ ] VirtualBox 7.x installed with Extension Pack
- [ ] Ubuntu 24.04 LTS Server ISO downloaded
- [ ] VM created: UEFI enabled, NVMe controller, 4 GB RAM, 2 CPUs
- [ ] OS installed with OpenSSH server
- [ ] VM network set to NAT (or bridged for SSH access)
- [ ] Can SSH into VM or have console access

## Installation

- [ ] `sudo apt update && sudo apt install -y git python3-venv` — succeeds
- [ ] `git clone https://github.com/nino79/batoi-classroom-suite.git` — succeeds
- [ ] `cd batoi-classroom-suite/cli` — directory exists
- [ ] `python3 -m venv .venv` — creates venv successfully
- [ ] `source .venv/bin/activate` — prompt changes
- [ ] `pip install -e ".[dev]"` — installs without error

## Commands to Demonstrate

### `bcs --help`
- [ ] Prints usage and full command tree
- [ ] Shows `doctor`, `inventory`, `validate`, `version`
- [ ] Shows stubs: `build`, `install`, `deploy`, `backup`, `restore`, `update`, `config`

### `bcs version`
- [ ] Prints version string (e.g. `0.1.0`)
- [ ] Shows commit hash, build date
- [ ] Shows supported config API versions

### `bcs validate`
- [ ] `bcs validate ../config/examples/default.yaml` exits 0
- [ ] `bcs validate --help` shows usage
- [ ] `bcs validate nonexistent.yaml` exits non-zero with clear error

### `bcs inventory`
- [ ] `bcs inventory` prints text table with all sections
- [ ] `bcs inventory --output json` prints valid JSON
- [ ] `bcs inventory --output yaml` prints valid YAML
- [ ] JSON output is parseable: `bcs inventory -o json | python3 -m json.tool`

### `bcs doctor`
- [ ] `bcs doctor` runs all checks and prints per-check status
- [ ] Shows at least one `[ OK ]` line
- [ ] Does not crash or hang
- [ ] `bcs doctor --check firmware` runs single check only

### Stubs (each should show help and refuse to run)
- [ ] `bcs build` prints "not implemented in this phase"
- [ ] `bcs install` prints "not implemented in this phase"
- [ ] `bcs deploy` prints "not implemented in this phase"
- [ ] `bcs backup` prints "not implemented in this phase"
- [ ] `bcs restore` prints "not implemented in this phase"
- [ ] `bcs update` prints "not implemented in this phase"
- [ ] `bcs config` prints subcommand help

## Edge Cases

- [ ] `bcs` (bare, no args) shows help, exits 0
- [ ] `bcs --help` = `bcs help` = `bcs` (same output)
- [ ] `bcs --version` prints version (not help)
- [ ] `bcs bogus` exits 8 with "unknown command" message
- [ ] `bcs -o json version` shows JSON version output
- [ ] `bcs -v inventory` shows debug logging on stderr

## Cleanup

- [ ] `deactivate` to leave venv
- [ ] VM can be discarded after demo (no persistent state needed)
