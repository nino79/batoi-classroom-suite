#!/usr/bin/env bash
# verify-build-layout.sh — Check that a Builder workspace has the correct
# directory structure, expected files, and valid YAML manifests.
#
# Unlike inspect-build.sh, this script is meant for CI gating: it returns
# a non-zero exit code for any structural problem.
#
# Usage:
#   ./scripts/builder/verify-build-layout.sh <workspace-dir>
#   ./scripts/builder/verify-build-layout.sh --strict <workspace-dir>
#
# Exit codes:
#   0  — all checks pass
#   1  — workspace not found
#   2  — missing required subdirectory
#   3  — missing required file
#   4  — invalid YAML
#   5  — checksum mismatch (--strict only)

set -euo pipefail
IFS=$'\n\t'

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/_shared.sh"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

STRICT=false
WORKSPACE=""

EXIT_CODE=0

# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------

usage() {
  cat >&2 <<EOF
Usage: $(basename "$0") [OPTIONS] <workspace-dir>

Verify a Builder workspace has the correct layout and valid files.

Options:
  --strict    Also verify checksums.sha256 against computed values
  -h, --help  Show this help message
EOF
}

check() {
  local desc="$1"
  shift
  if "$@"; then
    log_info "PASS: ${desc}"
  else
    log_error "FAIL: ${desc}"
    EXIT_CODE=1
  fi
}

check_fatal() {
  local desc="$1"
  local code="$2"
  shift 2
  if "$@"; then
    log_info "PASS: ${desc}"
  else
    log_error "FAIL: ${desc}"
    EXIT_CODE="${code}"
  fi
}

check_dir_exists() {
  local dir="$1"
  [[ -d "${dir}" ]]
}

check_file_exists() {
  local file="$1"
  [[ -f "${file}" ]]
}

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------

while [[ $# -gt 0 ]]; do
  case "$1" in
    --strict)
      STRICT=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    -*)
      log_error "Unknown option: $1"
      usage
      exit 1
      ;;
    *)
      if [[ -n "${WORKSPACE}" ]]; then
        log_error "Multiple workspace paths specified"
        usage
        exit 1
      fi
      WORKSPACE="$1"
      shift
      ;;
  esac
done

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if [[ -z "${WORKSPACE}" ]]; then
  log_error "No workspace directory specified"
  usage
  exit 1
fi

log_info "Verifying workspace: ${WORKSPACE}"

# Stage: workspace exists
check_fatal "Workspace directory exists" 1 check_dir_exists "${WORKSPACE}"

# Stage: required subdirectories exist
check_fatal "manifests/ subdirectory" 2 check_dir_exists "${WORKSPACE}/manifests"
check_fatal "metadata/ subdirectory" 2 check_dir_exists "${WORKSPACE}/metadata"
check_fatal "boot/ subdirectory" 2 check_dir_exists "${WORKSPACE}/boot"
check_fatal "artifacts/ subdirectory" 2 check_dir_exists "${WORKSPACE}/artifacts"

# Stage: required files in manifests/
check_fatal "manifests/packages.yaml" 3 check_file_exists "${WORKSPACE}/manifests/packages.yaml"
check_fatal "manifests/layout.yaml" 3 check_file_exists "${WORKSPACE}/manifests/layout.yaml"
check_fatal "manifests/boot-entries.yaml" 3 check_file_exists "${WORKSPACE}/manifests/boot-entries.yaml"

# Stage: required files in metadata/
check_fatal "metadata/provenance.json" 3 check_file_exists "${WORKSPACE}/metadata/provenance.json"
check_fatal "metadata/VERSION" 3 check_file_exists "${WORKSPACE}/metadata/VERSION"
check_fatal "metadata/build.log" 3 check_file_exists "${WORKSPACE}/metadata/build.log"

# Stage: YAML validity of manifests
check "packages.yaml is valid YAML" validate_yaml "${WORKSPACE}/manifests/packages.yaml"
check "layout.yaml is valid YAML" validate_yaml "${WORKSPACE}/manifests/layout.yaml"
check "boot-entries.yaml is valid YAML" validate_yaml "${WORKSPACE}/manifests/boot-entries.yaml"

# Stage: artifacts directory is not empty
check "artifacts/ contains files" \
  sh -c "find '${WORKSPACE}/artifacts' -type f 2>/dev/null | grep -q ."

# Stage: boot directory is not empty
check "boot/ contains files" \
  sh -c "find '${WORKSPACE}/boot' -type f 2>/dev/null | grep -q ."

# Stage: provenance is valid JSON
check "provenance.json is valid JSON" \
  python3 -c "import json; json.loads(open('${WORKSPACE}/metadata/provenance.json').read())"

# Stage: strict checksum verification
if ${STRICT} && [[ -f "${WORKSPACE}/metadata/checksums.sha256" ]]; then
  log_info "Verifying checksums.sha256..."
  while IFS= read -r line; do
    [[ -z "${line}" ]] && continue
    local expected_hash file_path
    expected_hash=$(echo "${line}" | cut -d' ' -f1)
    file_path=$(echo "${line}" | cut -d' ' -f3)
    local full_path="${WORKSPACE}/${file_path}"
    if [[ -f "${full_path}" ]]; then
      local actual_hash
      actual_hash=$(sha256_file "${full_path}")
      if [[ "${expected_hash}" == "${actual_hash}" ]]; then
        log_info "PASS: checksum ${file_path}"
      else
        log_error "FAIL: checksum mismatch for ${file_path}"
        log_error "  expected: ${expected_hash}"
        log_error "  actual:   ${actual_hash}"
        EXIT_CODE=5
      fi
    else
      log_error "FAIL: checksum references missing file: ${full_path}"
      EXIT_CODE=5
    fi
  done < "${WORKSPACE}/metadata/checksums.sha256"
elif ${STRICT}; then
  log_warn "No checksums.sha256 found; skipping checksum verification"
fi

# Summary
echo ""
if [[ "${EXIT_CODE}" -eq 0 ]]; then
  log_info "All layout checks passed."
else
  log_error "Layout verification failed with exit code ${EXIT_CODE}."
fi

exit "${EXIT_CODE}"
