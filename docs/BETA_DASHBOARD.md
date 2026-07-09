# Beta Diagnostics Dashboard

**Purpose:** Aggregate outputs from hardware validation, release tooling, and CLI validation into a single consolidated report for Beta release decision-making.

The dashboard script (`scripts/dashboard/build-dashboard.sh`) scans the repository for existing reports and artifacts, collects structured data, and generates:

| File | Format | Purpose |
|---|---|---|
| `reports/dashboard/dashboard.md` | Markdown | Full human-readable report — 8 sections |
| `reports/dashboard/dashboard.json` | JSON | Complete data for machine consumption |
| `reports/dashboard/summary.json` | JSON | Lightweight PASS/WARN/FAIL status summary |

## Workflow

### Quick start

```bash
# Build the dashboard (collects data, generates all outputs)
./scripts/dashboard/build-dashboard.sh

# Validate the dashboard structure
./scripts/dashboard/validate-dashboard.sh

# View the report
cat reports/dashboard/dashboard.md
```

### Rebuild without re-collecting

```bash
# Use existing dashboard.json to regenerate Markdown + summary
./scripts/dashboard/build-dashboard.sh --skip-collect
```

### Custom output directory

```bash
./scripts/dashboard/build-dashboard.sh --output /tmp/dashboard
```

## Script Reference

| Script | Purpose | Exit Codes |
|---|---|---|
| `build-dashboard.sh` | Orchestrate data collection and report generation | 0=ok, 1=missing dep, 3=build failed |
| `collect-results.sh` | Scan repository for existing reports, emit JSON | 0=ok, 1=missing dep, 2=collect failed |
| `validate-dashboard.sh` | Validate dashboard structure and content | 0=valid, 1=missing dep, 4=validation failed |

## Dashboard Sections

### 1. Repository Status

- Version (from `VERSION`)
- Git commit (short SHA)
- Current branch
- Last tag
- Working tree clean/dirty

### 2. Release Readiness

Aggregate PASS/WARN/FAIL decision based on:

| Condition | Effect |
|---|---|
| Working tree dirty | WARN |
| No CLI validation results | WARN |
| Validation commands failed | WARN |
| No build artifacts | WARN |
| No checksums on artifacts | WARN |
| No hardware captures | WARN |
| Unsupported hardware detected | FAIL |
| High/medium severity known issues | WARN |

### 3. Validation

- Commands executed count
- Passed/failed counts
- Report, environment, timings presence

Source: `reports/validation/`

### 4. Hardware

- Machines tested count
- UEFI/non-UEFI firmware breakdown
- Secure Boot enabled/disabled/unknown breakdown
- NVMe/no-NVMe storage breakdown
- Per-machine table (UEFI, Secure Boot, NVMe)
- Unsupported configurations list

Source: `hardware-validation/`

### 5. Packaging

- Wheel count and file listing
- Source distribution count and file listing
- SHA256 checksums presence

Source: `dist/`

### 6. Release Artifacts

- Release notes presence
- Dependency summary presence
- Installed files manifest presence

Source: `reports/release/`

### 7. Known Issues

- Count of documented limitations
- List of limitation titles
- Link to `docs/KNOWN_LIMITATIONS.md`

Source: `docs/KNOWN_LIMITATIONS.md`

### 8. Next Steps

Actionable suggestions for missing or incomplete sections.

## Example Output

```markdown
# Beta Diagnostics Dashboard

**Generated:** 2026-07-09T14:00:00+02:00

## Repository Status

| Property | Value |
|---|---|
| Version | 0.1.0 |
| Git Commit | a1b2c3d |
| Branch | main |
| Last Tag | v0.1.0 |
| Working Tree | ✅ Clean |

## Release Readiness

**Overall:** ⚠️ **WARN**

### Reasons

- No build artifacts found — run build-release.sh
- No hardware validation captures found — run capture-all.sh

## Validation

| Metric | Value |
|---|---|
| Commands executed | 7 |
| Passed | 6 |
| Failed | 1 |
| Report | ✅ Present |
```

## Detected Sources

The dashboard auto-detects these directories and gracefully handles missing ones:

| Directory | Contains | Used For |
|---|---|---|
| `hardware-validation/` | Per-machine capture directories | Hardware section |
| `reports/validation/` | `report.md`, `timings.json`, `environment.json` | Validation section |
| `reports/release/` | `release-notes.md`, `dependency-summary.txt`, `installed-files.txt` | Release section |
| `dist/` | `*.whl`, `*.tar.gz`, `SHA256SUMS.txt` | Packaging section |
| `docs/KNOWN_LIMITATIONS.md` | Known limitations | Known issues section |

If any source is missing, the dashboard still builds — the missing section is noted with a suggestion for how to generate it.

## Future Extension Points

1. **Trend tracking** — persist historical dashboard snapshots and detect regressions across builds
2. **CI integration** — run `build-dashboard.sh` as a GitHub Actions step and comment the summary on PRs
3. **HTML rendering** — convert `dashboard.md` to HTML with collapsible sections and charts
4. **Alerting** — emit machine-readable alerts when release readiness drops to FAIL
5. **Metric thresholds** — configurable PASS/WARN/FAIL thresholds per section
6. **Quality gate integration** — read `reports/release/dependency-summary.txt` and `installed-files.txt` for richer packaging metrics
