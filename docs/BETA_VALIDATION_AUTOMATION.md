# Beta Validation Automation

**Status:** Accepted · **Last updated:** 2026-07-09

## Purpose

The Beta validation automation provides a single-command workflow to:

1. Capture the host environment (OS, kernel, hypervisor, CPU, memory, installed tools).
2. Exercise every `bcs` CLI command and record its exit code, duration, stdout, and stderr.
3. Generate structured reports (`report.md`, `timings.json`) and raw artifacts (`inventory.json`, `inventory.yaml`, `doctor.txt`).
4. Archive all results into a timestamped directory for distribution or CI artifact publishing.

This replaces ad-hoc manual validation with a repeatable, auditable process — every Beta release candidate runs the same commands and produces the same report shape.

## Workflow

```
validate-beta.sh
  ├─ verify-environment.sh  → environment.json
  ├─ bcs version            → stdout/stderr/exit code/timing
  ├─ bcs --help             → stdout/stderr/exit code/timing
  ├─ bcs validate …         → stdout/stderr/exit code/timing
  ├─ bcs inventory           → stdout/stderr/exit code/timing
  ├─ bcs inventory --output json  → stdout/stderr/exit code/timing → inventory.json
  ├─ bcs inventory --output yaml  → stdout/stderr/exit code/timing → inventory.yaml
  ├─ bcs doctor              → stdout/stderr/exit code/timing → doctor.txt
  └─ generate reports
       ├─ report.md          — summary table with pass/fail icons
       ├─ timings.json       — machine-readable timing data
       └─ (named copies of key outputs)
```

## Scripts

### `scripts/verify-environment.sh`

Collects host metadata and emits a JSON object to stdout. Called by `validate-beta.sh` but also usable standalone.

**Keys emitted:** `timestamp`, `kernel`, `distribution`, `hypervisor`, `has_efi`, `cpu_cores`, `memory_mib`, `python_version`, `pip_version`, `git_version`, `tools` (per-tool version map).

**Exit codes:** 0 on success, 1 if a major field cannot be collected.

### `scripts/validate-beta.sh`

Orchestrator. Pre-flight checks (bcs executable, virtual environment), calls `verify-environment.sh`, runs every CLI command in sequence, captures per-command artifacts, generates summary report and timings JSON.

**Configuration:** `VALIDATION_DIR` environment variable (defaults to `reports/validation/`).

**Exit codes:** 0 all commands passed, 1 one or more commands failed, 2 bcs not found.

### `scripts/collect-artifacts.sh`

Archives a validation output directory into a timestamped sibling under `reports/archives/`. Copies every file from the source directory plus the `README.md`.

**Usage:** `./scripts/collect-artifacts.sh [source_dir]` — source defaults to `reports/validation/`.

## Generated Artifacts

All artifacts are written to the `VALIDATION_DIR` (default: `reports/validation/`):

| Artifact | Source | Format |
|----------|--------|--------|
| `report.md` | Generated | Markdown table |
| `environment.json` | `verify-environment.sh` | JSON |
| `inventory.json` | `bcs inventory --output json` | JSON |
| `inventory.yaml` | `bcs inventory --output yaml` | YAML |
| `doctor.txt` | `bcs doctor` | Plain text |
| `timings.json` | Generated | JSON |
| `<command>_stdout.txt` | Per-command capture | Plain text |
| `<command>_stderr.txt` | Per-command capture | Plain text |
| `<command>_rc.txt` | Per-command capture | Plain text (single integer) |
| `<command>_time.txt` | Per-command capture | Plain text (decimal seconds) |

## CI Integration

In a GitHub Actions workflow, after `cli/` is installed:

```yaml
- name: Beta validation
  run: ./scripts/validate-beta.sh
  env:
    VALIDATION_DIR: ${{ github.workspace }}/reports/validation

- name: Upload validation artifacts
  uses: actions/upload-artifact@v4
  with:
    name: beta-validation-${{ github.sha }}
    path: reports/validation/
```

The `timings.json` and `report.md` can also be published as a build summary or attached to a release.

## Verification Checklist

Before tagging a Beta release:

- [ ] `./scripts/validate-beta.sh` exits 0 from the repository root.
- [ ] `reports/validation/report.md` shows all commands passing.
- [ ] `reports/validation/environment.json` correctly reflects the host.
- [ ] `reports/validation/inventory.json` is valid JSON.
- [ ] `reports/validation/inventory.yaml` is valid YAML.
- [ ] At least one run has passed on Ubuntu 24.04 LTS.
- [ ] At least one run has passed on LliureX 23 (the target platform).

## Future Extensions

- **Parallel command execution** — run independent commands concurrently (e.g., `bcs inventory` and `bcs doctor`) to reduce wall-clock time.
- **Regression comparison** — diff `timings.json` or `inventory.json` against a known-good baseline to detect regressions.
- **Hardware matrix sweep** — invoke `validate-beta.sh` across every environment in `HARDWARE_VALIDATION_MATRIX.md` and collect cross-environment reports.
- **HTML report** — render `report.md` as styled HTML for CI artifact preview.
- **bats tests** — unit-test each script's functions using the invocation-guard pattern from `docs/standards/bash-style-guide.md`.
- **GitHub Actions reusable workflow** — package the three scripts into a callable composite action.
