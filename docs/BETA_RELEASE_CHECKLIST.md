# Beta Release Checklist — Batoi Classroom Suite

Checklist for declaring `bcs` CLI ready for Beta validation. Every item must be verified and checked off before the Beta phase begins. Use this alongside [VM_VALIDATION.md](VM_VALIDATION.md) for per-environment test cases and [HARDWARE_VALIDATION_MATRIX.md](HARDWARE_VALIDATION_MATRIX.md) for expected results.

---

## Installation

- [ ] `python3 -m venv .venv` creates a clean virtual environment on Ubuntu 24.04
- [ ] `pip install -e ".[dev]"` completes without error
- [ ] `pip install .` (production mode) completes without error
- [ ] `bcs --help` works immediately after install (venv activated)
- [ ] `bcs version` reports correct version, commit hash, and build date
- [ ] Installation on Debian 12 produces no unexpected errors (see [HARDWARE_VALIDATION_MATRIX.md](HARDWARE_VALIDATION_MATRIX.md) E05)
- [ ] Installation on LliureX 23 produces no unexpected errors (see E06)
- [ ] No `externally-managed-environment` errors outside venv

## CLI Startup

- [ ] `bcs` (bare, no arguments) shows help text, exits 0
- [ ] `bcs --help` shows full command tree (11 commands)
- [ ] `bcs --help` = `bcs help` = `bcs` (same output)
- [ ] `bcs --version` prints version (not help), exits 0
- [ ] `bcs -v inventory` produces debug log output on stderr
- [ ] `bcs -vv inventory` produces more verbose debug output
- [ ] `bcs comando-inventado` exits 8 with "unknown command"

## Validation

- [ ] `bcs validate ../config/examples/default.yaml` exits 0
- [ ] `bcs validate nonexistent.yaml` exits non-zero with "file not found" message
- [ ] `bcs validate --help` shows subcommand usage
- [ ] All fields in `default.yaml` pass semantic validation

## Inventory

- [ ] `bcs inventory` prints all 10 sections (text mode)
- [ ] Section headings: `identity`, `firmware`, `operatingSystem`, `cpu`, `memory`, `storage`, `network`, `efiSystemPartition`, `usbStorage`, `tooling`
- [ ] `bcs inventory --output json` produces valid JSON
- [ ] JSON output contains `schemaVersion: "bcs-inventory/v1alpha1"`
- [ ] JSON output is parseable: `python3 -m json.tool` succeeds
- [ ] `bcs inventory --output yaml` produces valid YAML
- [ ] YAML output is parseable: `python3 -c "import yaml; yaml.safe_load(...)"` succeeds
- [ ] `bcs inventory --output json > /tmp/inventory.json && python3 -m json.tool /tmp/inventory.json` succeeds (file round-trip)

## Doctor

- [ ] `bcs doctor` runs all 9 checks without crashing
- [ ] All 9 checks present: `firmware`, `secure-boot`, `esp`, `storage`, `usb-storage`, `network`, `tooling`, `permissions`, `config`
- [ ] Each check shows one of `[ OK ]`, `[WARN]`, or `[FAIL]`
- [ ] `bcs doctor --check firmware` runs only that check
- [ ] `bcs doctor --output json` produces valid JSON
- [ ] JSON output contains `schemaVersion: "bcs-cli/v1alpha1"`
- [ ] `bcs doctor` works as non-root user (some checks may warn)
- [ ] `bcs doctor` does not hang or exceed 5 seconds (see Performance)

## JSON Output

- [ ] `bcs version --output json` — valid JSON with schema version
- [ ] `bcs doctor --output json` — valid JSON with schema version
- [ ] `bcs inventory --output json` — valid JSON with schema version
- [ ] Every JSON output is parseable by `python3 -m json.tool`
- [ ] JSON schema versions match documented values (per [CLI.md](../docs/CLI.md))

## YAML Output

- [ ] `bcs version --output yaml` — valid YAML
- [ ] `bcs inventory --output yaml` — valid YAML
- [ ] YAML outputs are parseable by `python3 -c "import yaml; yaml.safe_load(...)"`

## Performance

- [ ] `time bcs doctor` — `real` < 5 seconds
- [ ] `time bcs inventory` — `real` < 5 seconds
- [ ] `time bcs version` — `real` < 2 seconds
- [ ] `time bcs validate ../config/examples/default.yaml` — `real` < 2 seconds

## Regression

- [ ] `bcs doctor; bcs inventory; bcs validate` run sequentially without cross-contamination
- [ ] Running `bcs doctor` twice produces identical results (deterministic)
- [ ] Running `bcs inventory` twice produces identical results (deterministic)

## Stubs

- [ ] `bcs build` — prints "not implemented in this phase", exits non-zero
- [ ] `bcs install` — same
- [ ] `bcs deploy` — same
- [ ] `bcs backup` — same
- [ ] `bcs restore` — same
- [ ] `bcs update` — same
- [ ] `bcs config` — shows subcommand help (different from other stubs; it has nested subcommands)
- [ ] Each stub's `--help` shows its documented usage text

## Documentation

- [ ] `bcs --help` output matches [CLI.md](../docs/CLI.md) command tree
- [ ] Exit codes match [CLI.md](../docs/CLI.md) § Exit Codes
- [ ] Inventory schema matches [HOST_INVENTORY.md](../docs/HOST_INVENTORY.md)
- [ ] Doctor checks match [doctor.py](../cli/src/bcs/commands/doctor.py) `_ALL_CHECKS` dict
- [ ] [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md) is up to date with current state
- [ ] [HARDWARE_VALIDATION_MATRIX.md](HARDWARE_VALIDATION_MATRIX.md) has been updated with any new findings
- [ ] [CHANGELOG.md](../CHANGELOG.md) has `[Unreleased]` entry for Beta preparation

## Packaging

- [ ] `cli/pyproject.toml` version matches release intent
- [ ] `cli/pyproject.toml` dependencies are pinned to compatible ranges
- [ ] `pip install -e ".[dev]"` installs all dev dependencies (Ruff, mypy, pytest)
- [ ] `pip install .` (no `[dev]`) installs only runtime dependencies

## VirtualBox Validation (E01)

- [ ] VM created per [VM_FIRST_BOOT.md](VM_FIRST_BOOT.md) — EFI enabled, NVMe controller
- [ ] BCS installed per [VM_INSTALLATION.md](VM_INSTALLATION.md)
- [ ] All 27 test cases in [VM_VALIDATION.md](VM_VALIDATION.md) executed and recorded
- [ ] Test log appended to [VM_TEST_LOG.md](VM_TEST_LOG.md)
- [ ] Any bugs found reported using [VM_BUG_REPORT_TEMPLATE.md](VM_BUG_REPORT_TEMPLATE.md)
- [ ] Snapshot taken after successful validation pass

## Physical Hardware Validation (E02, E03, E06)

- [ ] Validated on Ubuntu 24.04 physical, NVMe, UEFI, Secure Boot disabled (E02)
- [ ] Validated on Ubuntu 24.04 physical, NVMe, UEFI, Secure Boot enabled (E03)
- [ ] Validated on LliureX 23 physical (E06)
- [ ] Results recorded for each environment
- [ ] Per-environment caveats documented in [HARDWARE_VALIDATION_MATRIX.md](HARDWARE_VALIDATION_MATRIX.md)

---

## Sign-off

| Role | Name | Date | Signature |
|---|---|---|---|
| Validator | | | |
| Reviewer | | | |
