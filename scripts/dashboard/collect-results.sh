#!/usr/bin/env bash
# collect-results.sh — Collect all Beta validation results into structured JSON.
#
# Scans for existing reports in:
#   reports/validation/
#   reports/release/
#   reports/dashboard/
#   hardware-validation/
#   dist/
# and produces a JSON summary to stdout.
#
# Usage:
#   ./scripts/dashboard/collect-results.sh
#   ./scripts/dashboard/collect-results.sh --output /path/to/summary.json
#   ./scripts/dashboard/collect-results.sh --help
#
# Exit codes:
#   0 — Collection successful (missing sections are noted, not errors)
#   1 — Missing dependency

set -euo pipefail
IFS=$'\n\t'

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/_shared.sh"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OUTPUT_FILE=""

# ---------------------------------------------------------------------------
# Collection functions
# ---------------------------------------------------------------------------

collect_repository_info() {
  local version="0.0.0" commit="unknown" branch="unknown" tag="none" clean="unknown"

  version="$(safe_read_file "${PROJECT_ROOT}/VERSION" "0.0.0")"

  if command -v git &>/dev/null; then
    commit="$(git -C "${PROJECT_ROOT}" rev-parse --short HEAD 2>/dev/null || echo "unknown")"
    branch="$(git -C "${PROJECT_ROOT}" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")"
    tag="$(git -C "${PROJECT_ROOT}" describe --tags --abbrev=0 2>/dev/null || echo "none")"

    local status
    status="$(git -C "${PROJECT_ROOT}" status --porcelain 2>/dev/null || true)"
    if [[ -z "${status}" ]]; then
      clean="true"
    else
      clean="false"
    fi
  fi

  printf '{\n'
  printf '    "version": %s,\n' "$(json_string "${version}")"
  printf '    "git_commit": %s,\n' "$(json_string "${commit}")"
  printf '    "git_branch": %s,\n' "$(json_string "${branch}")"
  printf '    "git_tag": %s,\n' "$(json_string "${tag}")"
  printf '    "working_tree_clean": %s\n' "${clean}"
  printf '  }'
}

collect_validation_results() {
  local validation_dir="${PROJECT_ROOT}/reports/validation"

  if [[ ! -d "${validation_dir}" ]]; then
    printf '{"present": false, "report": null, "environment": null, "timings": null, "commands": 0, "passed": 0, "failed": 0}'
    return
  fi

  local report_file="${validation_dir}/report.md"
  local env_file="${validation_dir}/environment.json"
  local timings_file="${validation_dir}/timings.json"
  local report_present="false"
  local env_present="false"
  local timings_present="false"

  [[ -f "${report_file}" ]] && report_present="true"
  [[ -f "${env_file}" ]] && env_present="true"
  [[ -f "${timings_file}" ]] && timings_present="true"

  # Count command artifacts
  local cmd_count
  cmd_count="$(count_files "*_stdout.txt" "${validation_dir}")"

  # Count passed/failed from timings if available
  local passed=0 failed=0
  if [[ -f "${timings_file}" ]] && command -v python3 &>/dev/null; then
    local counts
    counts="$(python3 -c "
import json
with open('${timings_file}') as f:
    data = json.load(f)
cmds = data.get('commands', [])
passed = sum(1 for c in cmds if c.get('exit_code') == 0)
failed = sum(1 for c in cmds if c.get('exit_code') != 0)
print(f'{passed},{failed}')
" 2>/dev/null || echo "0,0")"
    passed="$(printf '%s' "${counts}" | cut -d',' -f1)"
    failed="$(printf '%s' "${counts}" | cut -d',' -f2)"
  fi

  printf '{\n'
  printf '    "present": true,\n'
  printf '    "report_present": %s,\n' "${report_present}"
  printf '    "environment_present": %s,\n' "${env_present}"
  printf '    "timings_present": %s,\n' "${timings_present}"
  printf '    "commands": %s,\n' "$(json_int "${cmd_count}")"
  printf '    "passed": %s,\n' "$(json_int "${passed}")"
  printf '    "failed": %s\n' "$(json_int "${failed}")"
  printf '  }'
}

collect_hardware_results() {
  local hw_dir="${PROJECT_ROOT}/hardware-validation"

  if [[ ! -d "${hw_dir}" ]]; then
    printf '{"present": false, "machines": 0, "machine_list": [], "uefi_count": 0, "non_uefi_count": 0, "sb_enabled": 0, "sb_disabled": 0, "nvme_count": 0, "no_nvme_count": 0, "unsupported": []}'
    return
  fi

  local machines=()
  local machine_count=0
  local uefi_count=0 non_uefi_count=0
  local sb_enabled=0 sb_disabled=0 sb_unknown=0
  local nvme_count=0 no_nvme_count=0
  local -a unsupported=()

  for machine_dir in "${hw_dir}"/*/; do
    [[ -d "${machine_dir}" ]] || continue
    local machine_name
    machine_name="$(basename "${machine_dir}")"
    local latest_capture=""
    local latest_ts=0

    # Find latest capture for this machine
    for capture_dir in "${machine_dir}"*/; do
      [[ -d "${capture_dir}" ]] || continue
      local ts
      ts="$(stat --format='%Y' "${capture_dir}" 2>/dev/null || echo "0")"
      if [[ "${ts}" -gt "${latest_ts}" ]]; then
        latest_ts="${ts}"
        latest_capture="${capture_dir}"
      fi
    done

    if [[ -z "${latest_capture}" ]]; then
      machines+=("${machine_name}|unknown|unknown|unknown|unknown|unknown")
      (( machine_count++ )) || true
      continue
    fi

    local fw_file="${latest_capture}firmware.json"
    local sys_file="${latest_capture}system.json"
    local storage_file="${latest_capture}storage.json"

    local uefi="unknown" sb="unknown" has_nvme="unknown"

    # Read firmware
    if [[ -f "${fw_file}" ]] && command -v python3 &>/dev/null; then
      uefi="$(python3 -c "import json; print(json.load(open('${fw_file}')).get('uefi','unknown'))" 2>/dev/null || echo "unknown")"
      sb="$(python3 -c "import json; print(json.load(open('${fw_file}')).get('secure_boot','unknown'))" 2>/dev/null || echo "unknown")"
    fi

    # Read storage
    if [[ -f "${storage_file}" ]] && command -v python3 &>/dev/null; then
      has_nvme="$(python3 -c "
import json
data = json.load(open('${storage_file}'))
devices = data.get('devices', [])
if isinstance(devices, dict):
    devices = devices.get('blockdevices', [])
for d in devices:
    if 'nvme' in d.get('name','').lower():
        print('yes')
        exit(0)
print('no')
" 2>/dev/null || echo "unknown")"
    fi

    # Count
    [[ "${uefi}" == "true" ]] && (( uefi_count++ )) || true
    [[ "${uefi}" != "true" ]] && (( non_uefi_count++ )) || true
    case "${sb}" in
      enabled)  (( sb_enabled++ )) || true ;;
      disabled) (( sb_disabled++ )) || true ;;
      *)        (( sb_unknown++ )) || true ;;
    esac
    [[ "${has_nvme}" == "yes" ]] && (( nvme_count++ )) || true
    [[ "${has_nvme}" == "no" ]] && (( no_nvme_count++ )) || true

    if [[ "${uefi}" != "true" ]]; then
      unsupported+=("${machine_name}: Not UEFI")
    fi

    machines+=("${machine_name}|${uefi}|${sb}|${has_nvme}")
    (( machine_count++ )) || true
  done

  # Build machine list JSON
  local machine_json="["
  local first=1
  for m in "${machines[@]}"; do
    if [[ ${first} -eq 0 ]]; then
      machine_json="${machine_json},"
    fi
    first=0
    IFS='|' read -r name uefi_val sb_val nvme_val <<< "${m}"
    machine_json="${machine_json}{\"name\":$(json_string "${name}"),\"uefi\":$(json_string "${uefi_val}"),\"secure_boot\":$(json_string "${sb_val}"),\"nvme\":$(json_string "${nvme_val}")}"
  done
  machine_json="${machine_json}]"

  # Build unsupported JSON
  local unsup_json="["
  first=1
  for u in "${unsupported[@]}"; do
    if [[ ${first} -eq 0 ]]; then
      unsup_json="${unsup_json},"
    fi
    first=0
    unsup_json="${unsup_json}$(json_string "${u}")"
  done
  unsup_json="${unsup_json}]"

  printf '{\n'
  printf '    "present": true,\n'
  printf '    "machines": %s,\n' "$(json_int "${machine_count}")"
  printf '    "machine_list": %s,\n' "${machine_json}"
  printf '    "uefi_count": %s,\n' "$(json_int "${uefi_count}")"
  printf '    "non_uefi_count": %s,\n' "$(json_int "${non_uefi_count}")"
  printf '    "sb_enabled": %s,\n' "$(json_int "${sb_enabled}")"
  printf '    "sb_disabled": %s,\n' "$(json_int "${sb_disabled}")"
  printf '    "sb_unknown": %s,\n' "$(json_int "${sb_unknown}")"
  printf '    "nvme_count": %s,\n' "$(json_int "${nvme_count}")"
  printf '    "no_nvme_count": %s,\n' "$(json_int "${no_nvme_count}")"
  printf '    "unsupported": %s\n' "${unsup_json}"
  printf '  }'
}

collect_package_results() {
  local dist_dir="${PROJECT_ROOT}/dist"

  if [[ ! -d "${dist_dir}" ]]; then
    printf '{"present": false, "wheels": 0, "sdist": 0, "checksums": null, "wheel_files": [], "sdist_files": []}'
    return
  fi

  local wheel_count sdist_count
  wheel_count="$(count_files "*.whl" "${dist_dir}")"
  sdist_count="$(count_files "*.tar.gz" "${dist_dir}")"

  local checksum_present="false"
  [[ -f "${dist_dir}/SHA256SUMS.txt" ]] && checksum_present="true"

  # List wheel files
  local wheel_json="["
  local first=1
  while IFS= read -r -d '' f; do
    if [[ ${first} -eq 0 ]]; then
      wheel_json="${wheel_json},"
    fi
    first=0
    local name size
    name="$(basename "${f}")"
    size="$(stat --format='%s' "${f}" 2>/dev/null || wc -c < "${f}" | tr -d ' ')"
    wheel_json="${wheel_json}{\"file\":$(json_string "${name}"),\"size_bytes\":$(json_int "${size}")}"
  done < <(find "${dist_dir}" -maxdepth 1 -type f -name "*.whl" -print0 2>/dev/null || true)
  wheel_json="${wheel_json}]"

  # List sdist files
  local sdist_json="["
  first=1
  while IFS= read -r -d '' f; do
    if [[ ${first} -eq 0 ]]; then
      sdist_json="${sdist_json},"
    fi
    first=0
    local name size
    name="$(basename "${f}")"
    size="$(stat --format='%s' "${f}" 2>/dev/null || wc -c < "${f}" | tr -d ' ')"
    sdist_json="${sdist_json}{\"file\":$(json_string "${name}"),\"size_bytes\":$(json_int "${size}")}"
  done < <(find "${dist_dir}" -maxlength 1 -type f -name "*.tar.gz" -print0 2>/dev/null || true)
  sdist_json="${sdist_json}]"

  printf '{\n'
  printf '    "present": true,\n'
  printf '    "wheels": %s,\n' "$(json_int "${wheel_count}")"
  printf '    "sdist": %s,\n' "$(json_int "${sdist_count}")"
  printf '    "checksums_present": %s,\n' "${checksum_present}"
  printf '    "wheel_files": %s,\n' "${wheel_json}"
  printf '    "sdist_files": %s\n' "${sdist_json}"
  printf '  }'
}

collect_release_results() {
  local release_dir="${PROJECT_ROOT}/reports/release"

  if [[ ! -d "${release_dir}" ]]; then
    printf '{"present": false, "release_notes": null, "dependency_summary": null, "installed_files": null}'
    return
  fi

  local notes_present="false" deps_present="false" files_present="false"
  [[ -f "${release_dir}/release-notes.md" ]] && notes_present="true"
  [[ -f "${release_dir}/dependency-summary.txt" ]] && deps_present="true"
  [[ -f "${release_dir}/installed-files.txt" ]] && files_present="true"

  printf '{\n'
  printf '    "present": true,\n'
  printf '    "release_notes_present": %s,\n' "${notes_present}"
  printf '    "dependency_summary_present": %s,\n' "${deps_present}"
  printf '    "installed_files_present": %s\n' "${files_present}"
  printf '  }'
}

collect_known_issues() {
  local kl_file="${PROJECT_ROOT}/docs/KNOWN_LIMITATIONS.md"

  if [[ ! -f "${kl_file}" ]]; then
    printf '{"present": false, "issues": 0, "items": []}'
    return
  fi

  # Count issues (## headings)
  local issue_count
  issue_count="$(grep -c '^## ' "${kl_file}" 2>/dev/null || echo "0")"

  # Collect issue titles
  local issues_json="["
  local first=1
  while IFS= read -r line; do
    local title="${line##\#\# }"
    title="${title%% --*}"
    title="$(printf '%s' "${title}" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    if [[ -n "${title}" ]]; then
      if [[ ${first} -eq 0 ]]; then issues_json="${issues_json},"; fi
      first=0
      issues_json="${issues_json}$(json_string "${title}")"
    fi
  done < <(grep '^## ' "${kl_file}" 2>/dev/null || true)
  issues_json="${issues_json}]"

  printf '{\n'
  printf '    "present": true,\n'
  printf '    "issues": %s,\n' "$(json_int "${issue_count}")"
  printf '    "items": %s\n' "${issues_json}"
  printf '  }'
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

main() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --help|-h)
        printf '%s\n\n' "Collect all Beta validation results into structured JSON."
        printf 'Usage:\n  %s [--output <file>]\n\n' "$0"
        printf 'Options:\n  --output, -o  Write JSON to file (default: stdout)\n'
        printf '  --help, -h    Print this help message\n'
        exit 0
        ;;
      --output|-o)
        OUTPUT_FILE="$2"
        shift 2
        ;;
      *)
        log_error "Unknown option: $1"; exit 1
        ;;
    esac
  done

  log_info "Collecting Beta validation results..."

  local repo validation hardware packaging release known_issues

  repo="$(collect_repository_info)"
  validation="$(collect_validation_results)"
  hardware="$(collect_hardware_results)"
  packaging="$(collect_package_results)"
  release="$(collect_release_results)"
  known_issues="$(collect_known_issues)"

  local timestamp
  timestamp="$(date --iso-8601=seconds 2>/dev/null || date -u +'%Y-%m-%dT%H:%M:%SZ')"

  local json
  json="$(
    printf '{\n'
    printf '  "generated_at": %s,\n' "$(json_string "${timestamp}")"
    printf '  "project_root": %s,\n' "$(json_string "${PROJECT_ROOT}")"
    printf '  "repository": %s,\n' "${repo}"
    printf '  "validation": %s,\n' "${validation}"
    printf '  "hardware": %s,\n' "${hardware}"
    printf '  "packaging": %s,\n' "${packaging}"
    printf '  "release": %s,\n' "${release}"
    printf '  "known_issues": %s\n' "${known_issues}"
    printf '}\n'
  )"

  if [[ -n "${OUTPUT_FILE}" ]]; then
    mkdir -p "$(dirname "${OUTPUT_FILE}")"
    printf '%s\n' "${json}" > "${OUTPUT_FILE}"
    log_info "Results written to ${OUTPUT_FILE}"
  else
    printf '%s\n' "${json}"
  fi
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
