#!/usr/bin/env bash
# validate-dashboard.sh — Validate the Beta Diagnostics Dashboard structure and
# content. Checks that all expected files exist, JSON is well-formed, and
# content is non-empty.
#
# Usage:
#   ./scripts/dashboard/validate-dashboard.sh
#   ./scripts/dashboard/validate-dashboard.sh --dir /path/to/dashboard
#   ./scripts/dashboard/validate-dashboard.sh --help
#
# Exit codes:
#   0 — Dashboard is valid
#   1 — Missing dependency
#   4 — Validation failed

set -euo pipefail
IFS=$'\n\t'

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/_shared.sh"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DASHBOARD_DIR="${PROJECT_ROOT}/reports/dashboard"
FAILED=0

# ---------------------------------------------------------------------------
# Validation checks
# ---------------------------------------------------------------------------

validate_file_exists() {
  local path="$1"
  local label="$2"

  if [[ -f "${path}" ]]; then
    log_pass "${label}: ${path}"
    return 0
  else
    log_fail "${label}: not found at ${path}"
    return 1
  fi
}

validate_file_not_empty() {
  local path="$1"
  local label="$2"

  if [[ ! -f "${path}" ]]; then
    return 1
  fi

  local size
  size="$(stat --format='%s' "${path}" 2>/dev/null || wc -c < "${path}" | tr -d ' ')"
  if [[ "${size}" -gt 0 ]]; then
    log_pass "${label}: ${size} bytes (non-empty)"
    return 0
  else
    log_fail "${label}: file is empty"
    return 1
  fi
}

validate_json() {
  local path="$1"
  local label="$2"

  if [[ ! -f "${path}" ]]; then
    return 1
  fi

  if command -v python3 &>/dev/null; then
    if python3 -c "import json; json.load(open('${path}'))" 2>/dev/null; then
      log_pass "${label}: valid JSON"
      return 0
    else
      log_fail "${label}: invalid JSON"
      return 1
    fi
  else
    # Basic validation without python3
    if head -1 "${path}" | grep -q '^{' && tail -1 "${path}" | grep -q '}$'; then
      log_pass "${label}: appears to be valid JSON (basic check)"
      return 0
    else
      log_warn "${label}: cannot fully validate JSON (python3 not available)"
      return 0
    fi
  fi
}

validate_json_has_keys() {
  local path="$1"
  local -a required_keys=("${@:2}")

  if [[ ! -f "${path}" ]]; then
    return 1
  fi

  if command -v python3 &>/dev/null; then
    local missing=0
    for key in "${required_keys[@]}"; do
      if ! python3 -c "import json; d=json.load(open('${path}')); assert '${key}' in d" 2>/dev/null; then
        log_fail "${path}: missing required key '${key}'"
        (( missing++ )) || true
      fi
    done
    if [[ "${missing}" -eq 0 ]]; then
      log_pass "${path}: all required keys present"
      return 0
    fi
    return 1
  fi
}

validate_markdown_structure() {
  local path="$1"

  if [[ ! -f "${path}" ]]; then
    return 1
  fi

  local heading_count section_count
  heading_count="$(grep -c '^## ' "${path}" 2>/dev/null || echo "0")"

  if [[ "${heading_count}" -lt 3 ]]; then
    log_fail "${path}: only ${heading_count} section headings (expected >= 3)"
    return 1
  fi

  log_pass "${path}: ${heading_count} section headings found"
}

validate_readiness_status() {
  local summary_json="${DASHBOARD_DIR}/summary.json"

  if [[ ! -f "${summary_json}" ]]; then
    return 1
  fi

  if command -v python3 &>/dev/null; then
    local status
    status="$(python3 -c "import json; print(json.load(open('${summary_json}')).get('status','UNKNOWN'))" 2>/dev/null || echo "UNKNOWN")"

    case "${status}" in
      PASS|WARN|FAIL)
        log_pass "Release readiness: ${status}"
        ;;
      *)
        log_warn "Release readiness: ${status} (unexpected value)"
        ;;
    esac
  fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

main() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --help|-h)
        printf '%s\n\n' "Validate the Beta Diagnostics Dashboard structure and content."
        printf 'Usage:\n  %s [--dir <path>]\n\n' "$0"
        printf 'Options:\n  --dir, -d    Dashboard directory (default: reports/dashboard/)\n'
        printf '  --help, -h   Print this help message\n'
        exit 0
        ;;
      --dir|-d)
        DASHBOARD_DIR="$2"
        shift 2
        ;;
      *)
        log_error "Unknown option: $1"; exit 1
        ;;
    esac
  done

  log_info "Validating Beta Diagnostics Dashboard — ${DASHBOARD_DIR}"
  printf '\n'

  # Check directory exists
  if [[ ! -d "${DASHBOARD_DIR}" ]]; then
    log_fail "Dashboard directory not found: ${DASHBOARD_DIR}"
    exit "${RC_VALIDATE_FAILED}"
  fi
  log_pass "Dashboard directory exists: ${DASHBOARD_DIR}"
  printf '\n'

  # Validate files exist and are non-empty
  local -a required_files=(
    "dashboard.md:Dashboard Markdown report"
    "dashboard.json:Dashboard data JSON"
    "summary.json:Dashboard summary JSON"
  )

  log_info "Checking required files..."
  for entry in "${required_files[@]}"; do
    local file label
    IFS=':' read -r file label <<< "${entry}"
    local path="${DASHBOARD_DIR}/${file}"

    validate_file_exists "${path}" "${label}" || (( FAILED++ )) || true
    if [[ -f "${path}" ]]; then
      validate_file_not_empty "${path}" "${label}" || (( FAILED++ )) || true
    fi
  done
  printf '\n'

  # Validate JSON structure
  log_info "Validating JSON structure..."
  validate_json "${DASHBOARD_DIR}/dashboard.json" "dashboard.json" || (( FAILED++ )) || true
  validate_json "${DASHBOARD_DIR}/summary.json" "summary.json" || (( FAILED++ )) || true
  printf '\n'

  # Validate JSON keys
  log_info "Checking required JSON keys..."
  validate_json_has_keys "${DASHBOARD_DIR}/dashboard.json" \
    "generated_at" "repository" "validation" "hardware" "packaging" "release" "known_issues" \
    || (( FAILED++ )) || true
  validate_json_has_keys "${DASHBOARD_DIR}/summary.json" "status" "reasons" \
    || (( FAILED++ )) || true
  printf '\n'

  # Validate Markdown structure
  log_info "Checking Markdown structure..."
  validate_markdown_structure "${DASHBOARD_DIR}/dashboard.md" || (( FAILED++ )) || true
  printf '\n'

  # Check readiness status
  log_info "Checking release readiness..."
  validate_readiness_status || (( FAILED++ )) || true
  printf '\n'

  # Summary
  log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  if [[ "${FAILED}" -eq 0 ]]; then
    log_info "Dashboard validation PASSED — all checks OK"
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit "${RC_OK}"
  else
    log_warn "Dashboard validation completed with ${FAILED} failure(s)"
    log_warn "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit "${RC_VALIDATE_FAILED}"
  fi
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
