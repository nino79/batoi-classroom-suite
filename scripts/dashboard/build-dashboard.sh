#!/usr/bin/env bash
# build-dashboard.sh — Build the complete Beta Diagnostics Dashboard.
#
# Orchestrates collect-results.sh to gather all data, then generates:
#   reports/dashboard/dashboard.md   — Human-readable Markdown report
#   reports/dashboard/dashboard.json — Full data as JSON
#   reports/dashboard/summary.json   — Lightweight status summary
#
# Usage:
#   ./scripts/dashboard/build-dashboard.sh
#   ./scripts/dashboard/build-dashboard.sh --output /path/to/dashboard
#   ./scripts/dashboard/build-dashboard.sh --skip-collect
#   ./scripts/dashboard/build-dashboard.sh --help
#
# Exit codes:
#   0 — Dashboard built successfully
#   1 — Missing dependency
#   3 — Build failed

set -euo pipefail
IFS=$'\n\t'

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/_shared.sh"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OUTPUT_DIR="${PROJECT_ROOT}/reports/dashboard"
SKIP_COLLECT=false
RAW_JSON=""

# ---------------------------------------------------------------------------
# Dashboard section generators
# ---------------------------------------------------------------------------

generate_dashboard_md() {
  local json="$1"
  local output="$2"

  local timestamp version commit branch tag clean
  local val_present val_passed val_failed
  local hw_present hw_machines hw_uefi hw_sb_enabled hw_sb_disabled hw_nvme hw_nonvme
  local pkg_present pkg_wheels pkg_sdist pkg_checksums
  local rel_present rel_notes rel_deps rel_files
  local kl_present kl_count

  # Parse JSON with python3 if available, otherwise use grep/sed
  if command -v python3 &>/dev/null; then
    timestamp="$(printf '%s' "${json}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('generated_at',''))" 2>/dev/null || echo "")"
    version="$(printf '%s' "${json}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['repository'].get('version',''))" 2>/dev/null || echo "")"
    commit="$(printf '%s' "${json}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['repository'].get('git_commit',''))" 2>/dev/null || echo "")"
    branch="$(printf '%s' "${json}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['repository'].get('git_branch',''))" 2>/dev/null || echo "")"
    tag="$(printf '%s' "${json}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['repository'].get('git_tag',''))" 2>/dev/null || echo "")"
    clean="$(printf '%s' "${json}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['repository'].get('working_tree_clean',''))" 2>/dev/null || echo "")"
    val_present="$(printf '%s' "${json}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['validation'].get('present',False))" 2>/dev/null || echo "false")"
    val_passed="$(printf '%s' "${json}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['validation'].get('passed',0))" 2>/dev/null || echo "0")"
    val_failed="$(printf '%s' "${json}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['validation'].get('failed',0))" 2>/dev/null || echo "0")"
    hw_present="$(printf '%s' "${json}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['hardware'].get('present',False))" 2>/dev/null || echo "false")"
    hw_machines="$(printf '%s' "${json}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['hardware'].get('machines',0))" 2>/dev/null || echo "0")"
    hw_uefi="$(printf '%s' "${json}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['hardware'].get('uefi_count',0))" 2>/dev/null || echo "0")"
    hw_sb_enabled="$(printf '%s' "${json}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['hardware'].get('sb_enabled',0))" 2>/dev/null || echo "0")"
    hw_sb_disabled="$(printf '%s' "${json}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['hardware'].get('sb_disabled',0))" 2>/dev/null || echo "0")"
    hw_nvme="$(printf '%s' "${json}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['hardware'].get('nvme_count',0))" 2>/dev/null || echo "0")"
    hw_nonvme="$(printf '%s' "${json}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['hardware'].get('no_nvme_count',0))" 2>/dev/null || echo "0")"
    pkg_present="$(printf '%s' "${json}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['packaging'].get('present',False))" 2>/dev/null || echo "false")"
    pkg_wheels="$(printf '%s' "${json}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['packaging'].get('wheels',0))" 2>/dev/null || echo "0")"
    pkg_sdist="$(printf '%s' "${json}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['packaging'].get('sdist',0))" 2>/dev/null || echo "0")"
    pkg_checksums="$(printf '%s' "${json}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['packaging'].get('checksums_present',False))" 2>/dev/null || echo "false")"
    rel_present="$(printf '%s' "${json}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['release'].get('present',False))" 2>/dev/null || echo "false")"
    rel_notes="$(printf '%s' "${json}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['release'].get('release_notes_present',False))" 2>/dev/null || echo "false")"
    rel_deps="$(printf '%s' "${json}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['release'].get('dependency_summary_present',False))" 2>/dev/null || echo "false")"
    rel_files="$(printf '%s' "${json}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['release'].get('installed_files_present',False))" 2>/dev/null || echo "false")"
    kl_present="$(printf '%s' "${json}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['known_issues'].get('present',False))" 2>/dev/null || echo "false")"
    kl_count="$(printf '%s' "${json}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['known_issues'].get('issues',0))" 2>/dev/null || echo "0")"

    # Also get machine list for detailed hardware table
    local machine_list_json
    machine_list_json="$(printf '%s' "${json}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d['hardware'].get('machine_list',[])))" 2>/dev/null || echo "[]")"

    # Get known issues list
    local issues_json
    issues_json="$(printf '%s' "${json}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d['known_issues'].get('items',[])))" 2>/dev/null || echo "[]")"

    # Dist files list
    local wheel_files_json sdist_files_json
    wheel_files_json="$(printf '%s' "${json}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d['packaging'].get('wheel_files',[])))" 2>/dev/null || echo "[]")"
    sdist_files_json="$(printf '%s' "${json}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d['packaging'].get('sdist_files',[])))" 2>/dev/null || echo "[]")"

    # Unsupported list
    local unsupported_json
    unsupported_json="$(printf '%s' "${json}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d['hardware'].get('unsupported',[])))" 2>/dev/null || echo "[]")"
  else
    # Fallback: minimal extraction without python3
    timestamp=""
    version=""
    commit=""
    branch=""
    tag=""
    clean=""
    val_present="false"
    val_passed="0"
    val_failed="0"
    hw_present="false"
    hw_machines="0"
    hw_uefi="0"
    hw_sb_enabled="0"
    hw_sb_disabled="0"
    hw_nvme="0"
    hw_nonvme="0"
    pkg_present="false"
    pkg_wheels="0"
    pkg_sdist="0"
    pkg_checksums="false"
    rel_present="false"
    rel_notes="false"
    rel_deps="false"
    rel_files="false"
    kl_present="false"
    kl_count="0"
    machine_list_json="[]"
    issues_json="[]"
    wheel_files_json="[]"
    sdist_files_json="[]"
    unsupported_json="[]"
  fi

  # Determine release readiness
  local readiness="PASS"
  local -a readiness_reasons=()

  if [[ "${clean}" == "false" ]]; then
    readiness="WARN"
    readiness_reasons+=("Uncommitted changes in working tree")
  fi

  if [[ "${val_present}" == "false" ]]; then
    readiness="WARN"
    readiness_reasons+=("CLI validation results not found — run validate-beta.sh")
  elif [[ "${val_failed}" -gt 0 ]]; then
    if [[ "${readiness}" != "FAIL" ]]; then readiness="WARN"; fi
    readiness_reasons+=("${val_failed} validation command(s) failed")
  fi

  if [[ "${pkg_present}" == "false" ]]; then
    readiness="WARN"
    readiness_reasons+=("No build artifacts found — run build-release.sh")
  fi

  if [[ "${pkg_checksums}" == "false" ]] && [[ "${pkg_present}" == "true" ]]; then
    readiness="WARN"
    readiness_reasons+=("No SHA256 checksums for build artifacts")
  fi

  if [[ "${hw_present}" == "false" ]]; then
    readiness="WARN"
    readiness_reasons+=("No hardware validation captures found — run capture-all.sh")
  fi

  local hw_unsupported_count=0
  if command -v python3 &>/dev/null; then
    hw_unsupported_count="$(printf '%s' "${unsupported_json}" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")"
  fi
  if [[ "${hw_unsupported_count}" -gt 0 ]]; then
    readiness="FAIL"
    readiness_reasons+=("${hw_unsupported_count} unsupported hardware configuration(s) detected")
  fi

  if [[ "${kl_count}" -gt 0 ]]; then
    local high_severity=0
    if command -v python3 &>/dev/null; then
      high_severity="$(printf '%s' "${json}" | python3 -c "
import sys,json
text = open('${PROJECT_ROOT}/docs/KNOWN_LIMITATIONS.md').read()
high = text.count('**Severity:** High') + text.count('**Severity:** Medium')
print(high)
" 2>/dev/null || echo "0")"
    fi
    if [[ "${high_severity}" -gt 0 ]]; then
      if [[ "${readiness}" != "FAIL" ]]; then
        readiness="WARN"
      fi
      readiness_reasons+=("${high_severity} medium/high severity known limitation(s)")
    fi
  fi

  if [[ ${#readiness_reasons[@]} -eq 0 ]]; then
    readiness_reasons+=("All checks passed")
  fi

  # Build reasons string
  local reasons_text=""
  for r in "${readiness_reasons[@]}"; do
    reasons_text="${reasons_text}- ${r}\n"
  done

  # --- Generate Markdown ---
  {
    printf '# Beta Diagnostics Dashboard\n\n'
    printf '**Generated:** %s  \n' "${timestamp}"
    printf '\n'

    # === Section 1: Repository Status ===
    printf '## Repository Status\n\n'
    md_table_header "Property" "Value"
    md_table_row "Version" "${version}"
    md_table_row "Git Commit" "${commit}"
    md_table_row "Branch" "${branch}"
    md_table_row "Last Tag" "${tag}"
    md_table_row "Working Tree" "$(if [[ "${clean}" == "true" ]]; then printf '✅ Clean'; else printf '❌ Dirty'; fi)"

    printf '\n'

    # === Section 2: Release Readiness ===
    printf '## Release Readiness\n\n'
    local badge=""
    case "${readiness}" in
      PASS) badge="✅ **PASS**" ;;
      WARN) badge="⚠️ **WARN**" ;;
      FAIL) badge="❌ **FAIL**" ;;
    esac
    printf '**Overall:** %s\n\n' "${badge}"
    printf '### Reasons\n\n'
    printf '%b\n' "${reasons_text}"

    # === Section 3: Validation ===
    printf '## Validation\n\n'
    if [[ "${val_present}" == "true" ]]; then
      printf '| Metric | Value |\n|---|---|\n'
      printf '| Commands executed | %s |\n' "$(printf '%s' "${json}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['validation'].get('commands',0))" 2>/dev/null || echo "0")"
      printf '| Passed | %s |\n' "${val_passed}"
      printf '| Failed | %s |\n' "${val_failed}"
      printf '| Report | ✅ Present |\n'
      printf '| Environment | ✅ Present |\n'
      printf '| Timings | ✅ Present |\n'
      printf '\nSee [validation report](../validation/report.md) for details.\n'
    else
      printf '_No validation results found._\n'
      printf '\nRun `scripts/validate-beta.sh` to generate validation reports.\n'
    fi
    printf '\n'

    # === Section 4: Hardware ===
    printf '## Hardware\n\n'
    if [[ "${hw_present}" == "true" ]]; then
      printf '| Metric | Value |\n|---|---|\n'
      printf '| Machines tested | %s |\n' "${hw_machines}"
      printf '| UEFI firmware | %s |\n' "${hw_uefi}"
      printf '| Non-UEFI firmware | %s |\n' "$(printf '%s' "${json}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['hardware'].get('non_uefi_count',0))" 2>/dev/null || echo "0")"
      printf '| Secure Boot enabled | %s |\n' "${hw_sb_enabled}"
      printf '| Secure Boot disabled | %s |\n' "${hw_sb_disabled}"
      printf '| NVMe storage | %s |\n' "${hw_nvme}"
      printf '| No NVMe storage | %s |\n' "${hw_nonvme}"

      printf '\n### Machines\n\n'
      md_table_header "Machine" "UEFI" "Secure Boot" "NVMe"
      if command -v python3 &>/dev/null; then
        printf '%s' "${machine_list_json}" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for m in data:
    name = m.get('name','?')
    uefi = '✅' if m.get('uefi') == 'true' else '❌'
    sb = m.get('secure_boot','?')
    nvme = '✅' if m.get('nvme') == 'yes' else ('❌' if m.get('nvme') == 'no' else '?')
    print(f'| {name} | {uefi} | {sb} | {nvme} |')
" 2>/dev/null
      fi

      if [[ "${hw_unsupported_count}" -gt 0 ]]; then
        printf '\n### Unsupported Configurations\n\n'
        printf '%s' "${unsupported_json}" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for item in data:
    print(f'- ⚠️ {item}')
" 2>/dev/null
      fi
    else
      printf '_No hardware validation captures found._\n'
      printf '\nRun `scripts/hardware-validation/capture-all.sh` to generate captures.\n'
    fi
    printf '\n'

    # === Section 5: Packaging ===
    printf '## Packaging\n\n'
    if [[ "${pkg_present}" == "true" ]]; then
      printf '| Metric | Value |\n|---|---|\n'
      printf '| Wheels | %s |\n' "${pkg_wheels}"
      printf '| Source distributions | %s |\n' "${pkg_sdist}"
      printf '| SHA256 checksums | %s |\n' "$(if [[ "${pkg_checksums}" == "true" ]]; then printf '✅ Present'; else printf '❌ Missing'; fi)"

      if [[ "${pkg_wheels}" -gt 0 ]]; then
        printf '\n### Wheel Files\n\n'
        md_table_header "File" "Size"
        printf '%s' "${wheel_files_json}" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for f in data:
    name = f.get('file','')
    size = f.get('size_bytes',0)
    size_str = f'{size} B'
    if size >= 1048576:
        size_str = f'{size / 1048576:.1f} MiB'
    elif size >= 1024:
        size_str = f'{size / 1024:.1f} KiB'
    print(f'| {name} | {size_str} |')
" 2>/dev/null
      fi

      if [[ "${pkg_sdist}" -gt 0 ]]; then
        printf '\n### Source Distributions\n\n'
        md_table_header "File" "Size"
        printf '%s' "${sdist_files_json}" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for f in data:
    name = f.get('file','')
    size = f.get('size_bytes',0)
    size_str = f'{size} B'
    if size >= 1048576:
        size_str = f'{size / 1048576:.1f} MiB'
    elif size >= 1024:
        size_str = f'{size / 1024:.1f} KiB'
    print(f'| {name} | {size_str} |')
" 2>/dev/null
      fi
    else
      printf '_No build artifacts found._\n'
      printf '\nRun `scripts/release/build-release.sh` to build packages.\n'
    fi
    printf '\n'

    # === Section 6: Release ===
    printf '## Release Artifacts\n\n'
    if [[ "${rel_present}" == "true" ]]; then
      md_table_header "Artifact" "Status"
      md_table_row "Release Notes" "$(if [[ "${rel_notes}" == "true" ]]; then printf '✅ Present'; else printf '❌ Missing'; fi)"
      md_table_row "Dependency Summary" "$(if [[ "${rel_deps}" == "true" ]]; then printf '✅ Present'; else printf '❌ Missing'; fi)"
      md_table_row "Installed Files" "$(if [[ "${rel_files}" == "true" ]]; then printf '✅ Present'; else printf '❌ Missing'; fi)"
    else
      printf '_No release artifacts found._\n'
      printf '\nRun `scripts/release/generate-release-notes.sh` and `scripts/release/verify-package.sh` to generate release artifacts.\n'
    fi
    printf '\n'

    # === Section 7: Known Issues ===
    printf '## Known Issues\n\n'
    if [[ "${kl_present}" == "true" ]] && [[ "${kl_count}" -gt 0 ]]; then
      printf '**%s documented limitation(s):**\n\n' "${kl_count}"
      if command -v python3 &>/dev/null; then
        printf '%s' "${issues_json}" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for i, title in enumerate(data, 1):
    print(f'{i}. {title}')
" 2>/dev/null
      fi
      printf '\nSee [KNOWN_LIMITATIONS.md](../KNOWN_LIMITATIONS.md) for full details.\n'
    else
      printf '_No known limitations documented._\n'
    fi
    printf '\n'

    # === Section 8: Next Steps ===
    printf '## Next Steps\n\n'
    local steps=""
    if [[ "${val_present}" == "false" ]]; then
      steps="${steps}- Run `scripts/validate-beta.sh` to generate validation results\n"
    fi
    if [[ "${hw_present}" == "false" ]]; then
      steps="${steps}- Run `scripts/hardware-validation/capture-all.sh` to capture hardware topology\n"
    fi
    if [[ "${pkg_present}" == "false" ]]; then
      steps="${steps}- Run `scripts/release/build-release.sh` to build packages\n"
    fi
    if [[ "${rel_notes}" == "false" ]]; then
      steps="${steps}- Run `scripts/release/generate-release-notes.sh` to generate release notes\n"
    fi
    if [[ "${clean}" == "false" ]]; then
      steps="${steps}- Commit or stash working tree changes before release\n"
    fi
    if [[ -z "${steps}" ]]; then
      steps="_All sections populated — no immediate action required._\n"
    fi
    printf '%b' "${steps}"
  } > "${output}"
}

generate_summary_json() {
  local json="$1"
  local output="$2"

  # Determine PASS/WARN/FAIL
  local readiness="PASS"
  local -a reasons=()

  local clean val_present val_failed hw_present hw_unsupported pkg_present
  if command -v python3 &>/dev/null; then
    clean="$(printf '%s' "${json}" | python3 -c "import sys,json; print(json.load(sys.stdin)['repository'].get('working_tree_clean','false'))" 2>/dev/null || echo "false")"
    val_present="$(printf '%s' "${json}" | python3 -c "import sys,json; print(json.load(sys.stdin)['validation'].get('present',False))" 2>/dev/null || echo "false")"
    val_failed="$(printf '%s' "${json}" | python3 -c "import sys,json; print(json.load(sys.stdin)['validation'].get('failed',0))" 2>/dev/null || echo "0")"
    hw_present="$(printf '%s' "${json}" | python3 -c "import sys,json; print(json.load(sys.stdin)['hardware'].get('present',False))" 2>/dev/null || echo "false")"
    hw_unsupported="$(printf '%s' "${json}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d['hardware'].get('unsupported',[])))" 2>/dev/null || echo "0")"
    pkg_present="$(printf '%s' "${json}" | python3 -c "import sys,json; print(json.load(sys.stdin)['packaging'].get('present',False))" 2>/dev/null || echo "false")"
  else
    clean="false"; val_present="false"; val_failed="0"; hw_present="false"; hw_unsupported="0"; pkg_present="false"
  fi

  if [[ "${clean}" == "false" ]]; then readiness="WARN"; reasons+=("dirty working tree"); fi
  if [[ "${val_present}" == "false" ]]; then readiness="WARN"; reasons+=("no validation"); fi
  if [[ "${val_failed}" -gt 0 ]]; then readiness="WARN"; reasons+=("${val_failed} test(s) failed"); fi
  if [[ "${hw_present}" == "false" ]]; then readiness="WARN"; reasons+=("no hardware captures"); fi
  if [[ "${hw_unsupported}" -gt 0 ]]; then readiness="FAIL"; reasons+=("${hw_unsupported} unsupported config(s)"); fi
  if [[ "${pkg_present}" == "false" ]]; then readiness="WARN"; reasons+=("no build artifacts"); fi

  if [[ ${#reasons[@]} -eq 0 ]]; then
    reasons+=("all checks passed")
  fi

  {
    printf '{\n'
    printf '  "status": %s,\n' "$(json_string "${readiness}")"
    printf '  "reasons": [\n'
    local first=1
    for r in "${reasons[@]}"; do
      if [[ ${first} -eq 0 ]]; then printf ',\n'; fi
      first=0
      printf '    %s' "$(json_string "${r}")"
    done
    printf '\n  ]\n'
    printf '}\n'
  } > "${output}"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

main() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --help|-h)
        printf '%s\n\n' "Build the complete Beta Diagnostics Dashboard."
        printf 'Usage:\n  %s [--output <dir>] [--skip-collect]\n\n' "$0"
        printf 'Options:\n'
        printf '  --output, -o    Output directory (default: reports/dashboard/)\n'
        printf '  --skip-collect  Skip data collection, use existing dashboard.json\n'
        printf '  --help, -h      Print this help message\n'
        exit 0
        ;;
      --output|-o)
        OUTPUT_DIR="$2"
        shift 2
        ;;
      --skip-collect)
        SKIP_COLLECT=true
        shift
        ;;
      *)
        log_error "Unknown option: $1"; exit 1
        ;;
    esac
  done

  mkdir -p "${OUTPUT_DIR}"

  # Collect raw data
  if [[ "${SKIP_COLLECT}" == true ]]; then
    local existing="${OUTPUT_DIR}/dashboard.json"
    if [[ -f "${existing}" ]]; then
      RAW_JSON="$(cat "${existing}")"
      log_info "Using existing dashboard.json"
    else
      log_error "No existing dashboard.json found in ${OUTPUT_DIR}"
      exit "${RC_BUILD_FAILED}"
    fi
  else
    log_info "Collecting validation results..."
    RAW_JSON="$(bash "${SCRIPT_DIR}/collect-results.sh" 2>/dev/null)" || {
      log_error "Failed to collect results"
      exit "${RC_COLLECT_FAILED}"
    }
  fi

  # Write dashboard.json
  local dashboard_json="${OUTPUT_DIR}/dashboard.json"
  printf '%s\n' "${RAW_JSON}" > "${dashboard_json}"
  log_info "Dashboard JSON written to ${dashboard_json}"

  # Generate dashboard.md
  local dashboard_md="${OUTPUT_DIR}/dashboard.md"
  generate_dashboard_md "${RAW_JSON}" "${dashboard_md}"
  log_info "Dashboard Markdown written to ${dashboard_md}"

  # Generate summary.json
  local summary_json="${OUTPUT_DIR}/summary.json"
  generate_summary_json "${RAW_JSON}" "${summary_json}"
  log_info "Summary JSON written to ${summary_json}"

  # Determine readiness
  local readiness
  readiness="$(python3 -c "import json; print(json.load(open('${summary_json}')).get('status','UNKNOWN'))" 2>/dev/null || echo "UNKNOWN")"

  log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  log_info "Dashboard built — Release readiness: ${readiness}"
  log_info "Output: ${OUTPUT_DIR}/"
  log_info "  dashboard.md   — Full human-readable report"
  log_info "  dashboard.json — Complete data as JSON"
  log_info "  summary.json   — Lightweight status summary"
  log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
