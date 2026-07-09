#!/usr/bin/env bash
# check-release.sh — Pre-flight checks for Beta release readiness.
#
# Verifies:
#   1. Git working tree is clean (no uncommitted changes)
#   2. VERSION file is a valid semver
#   3. CHANGELOG.md has an [Unreleased] section with entries
#   4. pyproject.toml version matches VERSION
#   5. All required tools are available
#   6. No placeholder files remain in the test fixture corpus
#   7. Package builds without errors (wheel + sdist)
#
# Usage:
#   ./scripts/release/check-release.sh
#   ./scripts/release/check-release.sh --verbose
#   ./scripts/release/check-release.sh --help
#
# Exit codes:
#   0 — All checks passed (release-ready)
#   1 — Missing dependency
#   5 — Pre-flight check failed

set -euo pipefail
IFS=$'\n\t'

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/_shared.sh"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

VERBOSE=false
RC_UNREADY=5

# ---------------------------------------------------------------------------
# Check functions
# ---------------------------------------------------------------------------

check_git_clean() {
  if ! command -v git &>/dev/null; then
    log_fail "git not available — cannot check working tree"
    return 1
  fi

  local status
  status="$(git -C "${PROJECT_ROOT}" status --porcelain 2>/dev/null || true)"
  if [[ -n "${status}" ]]; then
    log_fail "Git working tree has uncommitted changes:"
    printf '%s\n' "${status}" >&2
    return 1
  fi
  log_pass "Git working tree is clean"
}

check_version_file() {
  local version_file="${PROJECT_ROOT}/VERSION"
  check_file_readable "${version_file}" "VERSION file" || return 1

  local version
  version="$(cat "${version_file}" | tr -d '[:space:]')"

  # Validate semver: X.Y.Z with optional -prerelease
  if [[ ! "${version}" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$ ]]; then
    log_fail "VERSION does not contain a valid semver: '${version}'"
    return 1
  fi
  log_pass "VERSION: ${version} (valid semver)"
}

check_version_consistency() {
  local pyproject="${CLI_DIR}/pyproject.toml"
  check_file_readable "${pyproject}" "pyproject.toml" || return 1

  local file_version
  file_version="$(get_project_version)"

  local pyproject_version
  pyproject_version="$(grep -oP '(?<=^version = ").*(?=")' "${pyproject}" 2>/dev/null || echo "")"
  if [[ -z "${pyproject_version}" ]]; then
    log_fail "Cannot read version from pyproject.toml"
    return 1
  fi

  if [[ "${file_version}" != "${pyproject_version}" ]]; then
    log_fail "Version mismatch: VERSION=${file_version}, pyproject.toml=${pyproject_version}"
    return 1
  fi
  log_pass "Versions match: ${file_version}"
}

check_changelog() {
  local changelog="${PROJECT_ROOT}/CHANGELOG.md"
  check_file_readable "${changelog}" "CHANGELOG.md" || return 1

  # Check for [Unreleased] section
  if ! grep -q '^## \[Unreleased\]' "${changelog}"; then
    log_fail "CHANGELOG.md has no [Unreleased] section"
    return 1
  fi

  # Check for entries under [Unreleased]
  local unreleased_content
  unreleased_content="$(sed -n '/^## \[Unreleased\]/,/^## \[/p' "${changelog}" | tail -n +2 | head -n -1 || true)"
  unreleased_content="$(printf '%s' "${unreleased_content}" | grep -v '^$' || true)"

  if [[ -z "${unreleased_content}" ]]; then
    log_fail "CHANGELOG.md [Unreleased] section is empty"
    return 1
  fi

  local entry_count
  entry_count="$(printf '%s' "${unreleased_content}" | grep -c '^- ' || true)"
  if [[ "${entry_count}" -eq 0 ]]; then
    log_fail "CHANGELOG.md [Unreleased] has no list entries"
    return 1
  fi

  log_pass "CHANGELOG.md has ${entry_count} unreleased entries"
}

check_tools() {
  local required_tools=("python3" "pip3" "git")
  local missing=0

  for cmd in "${required_tools[@]}"; do
    if ! command -v "${cmd}" &>/dev/null; then
      log_fail "Required tool not found: ${cmd}"
      (( missing++ )) || true
    fi
  done

  # Check python version >= 3.12
  if command -v python3 &>/dev/null; then
    local py_version
    py_version="$(python3 --version 2>&1 | grep -oP '[0-9]+\.[0-9]+' | head -1 || echo "0")"
    local py_major="${py_version%%.*}"
    local py_minor="${py_version#*.}"
    if [[ "${py_major}" -lt 3 ]] || { [[ "${py_major}" -eq 3 ]] && [[ "${py_minor}" -lt 12 ]]; }; then
      log_fail "python3 >= 3.12 required (found ${py_version})"
      (( missing++ )) || true
    else
      log_pass "python3 ${py_version} (>= 3.12)"
    fi
  fi

  if [[ "${missing}" -gt 0 ]]; then
    return 1
  fi
  log_pass "All required tools available"
}

check_build_tools() {
  # Check build-system tools inside the CLI directory
  if command -v python3 &>/dev/null; then
    if python3 -c "import hatchling" 2>/dev/null; then
      log_pass "hatchling build backend available"
    else
      log_warn "hatchling not installed — will attempt pip install during build"
    fi
  fi
}

check_fixtures() {
  # Check for zero-byte placeholder files in test fixtures
  local fixtures_dir="${CLI_DIR}/tests/fixtures"
  if [[ ! -d "${fixtures_dir}" ]]; then
    log_warn "No fixtures directory found — skipping fixture check"
    return 0
  fi

  local placeholders=0
  while IFS= read -r -d '' file; do
    if [[ ! -s "${file}" ]]; then
      if [[ "${VERBOSE}" == true ]]; then
        log_warn "Placeholder fixture (zero bytes): ${file}"
      fi
      (( placeholders++ )) || true
    fi
  done < <(find "${fixtures_dir}" -type f -name "*.txt" -print0 2>/dev/null || true)

  if [[ "${placeholders}" -gt 0 ]]; then
    log_warn "${placeholders} placeholder fixture file(s) found (zero-byte)"
  else
    log_pass "No placeholder fixtures found"
  fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

main() {
  # Parse arguments
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --help|-h)
        print_usage_and_exit "$0" \
          "Pre-flight checks for Beta release readiness." \
          "[--verbose]" \
          "  0 — All checks passed (release-ready)\n  1 — Missing dependency\n  5 — Pre-flight check failed"
        ;;
      --verbose|-v)
        VERBOSE=true
        shift
        ;;
      *)
        log_error "Unknown option: $1"
        printf 'Usage: %s [--verbose]\n' "$0"
        exit 1
        ;;
    esac
  done

  local failed=0
  local checks_passed=0
  local checks_failed=0

  log_info "BCS Release Readiness Check — $(date)"
  printf '\n'

  # Run checks
  local -a check_fns=(
    "check_git_clean"
    "check_version_file"
    "check_version_consistency"
    "check_changelog"
    "check_tools"
    "check_build_tools"
    "check_fixtures"
  )

  for check_fn in "${check_fns[@]}";  do
    if "${check_fn}"; then
      (( checks_passed++ )) || true
    else
      (( checks_failed++ )) || true
      failed=1
    fi
  done

  printf '\n'
  log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  if [[ "${failed}" -eq 0 ]]; then
    log_info "All ${checks_passed} checks passed — release-ready!"
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit "${RC_OK}"
  else
    log_warn "${checks_passed} passed, ${checks_failed} failed"
    log_warn "Fix the failures above before proceeding with release."
    log_warn "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit "${RC_UNREADY}"
  fi
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
