#!/usr/bin/env bash
# build-release.sh — Build Python wheel and sdist packages for release.
#
# Builds the bcs CLI package (wheel + source distribution) into a clean
# output directory, verifies the artifacts exist, and computes SHA256 sums.
#
# Usage:
#   ./scripts/release/build-release.sh
#   ./scripts/release/build-release.sh --output /path/to/artifacts
#   ./scripts/release/build-release.sh --skip-clean
#   ./scripts/release/build-release.sh --help
#
# Exit codes:
#   0 — Build successful
#   1 — Missing dependency
#   2 — Build failed
#   4 — Cleanup failed

set -euo pipefail
IFS=$'\n\t'

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/_shared.sh"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OUTPUT_DIR="${PROJECT_ROOT}/dist"
SKIP_CLEAN=false
BUILD_DIR=""

# ---------------------------------------------------------------------------
# Build functions
# ---------------------------------------------------------------------------

clean_build() {
  local build_dir="$1"
  if [[ "${SKIP_CLEAN}" == true ]]; then
    log_info "Skipping clean (--skip-clean)"
    return 0
  fi

  if [[ -d "${build_dir}" ]]; then
    log_info "Cleaning build directory: ${build_dir}"
    rm -rf "${build_dir}"/* 2>/dev/null || {
      log_warn "Could not remove all files from ${build_dir}"
      return "${RC_CLEANUP_FAILED}"
    }
  fi
  mkdir -p "${build_dir}"
}

build_wheel() {
  local cli_dir="$1"
  local build_dir="$2"

  log_info "Building wheel..."
  cd "${cli_dir}"

  if ! python3 -m build --wheel --outdir "${build_dir}" 2>&1; then
    cd "${PROJECT_ROOT}"
    log_error "Wheel build failed"
    return "${RC_BUILD_FAILED}"
  fi

  cd "${PROJECT_ROOT}"
  log_info "Wheel build complete"
}

build_sdist() {
  local cli_dir="$1"
  local build_dir="$2"

  log_info "Building source distribution..."
  cd "${cli_dir}"

  if ! python3 -m build --sdist --outdir "${build_dir}" 2>&1; then
    cd "${PROJECT_ROOT}"
    log_error "Source distribution build failed"
    return "${RC_BUILD_FAILED}"
  fi

  cd "${PROJECT_ROOT}"
  log_info "Source distribution build complete"
}

verify_artifacts() {
  local build_dir="$1"
  local wheel_count sdist_count

  wheel_count="$(find "${build_dir}" -name '*.whl' -type f 2>/dev/null | wc -l)"
  sdist_count="$(find "${build_dir}" -name '*.tar.gz' -type f 2>/dev/null | wc -l)"

  if [[ "${wheel_count}" -eq 0 ]]; then
    log_fail "No wheel files found in ${build_dir}"
    return "${RC_BUILD_FAILED}"
  fi

  if [[ "${sdist_count}" -eq 0 ]]; then
    log_fail "No source distribution files found in ${build_dir}"
    return "${RC_BUILD_FAILED}"
  fi

  log_pass "Found ${wheel_count} wheel(s), ${sdist_count} source distribution(s)"
}

compute_checksums() {
  local build_dir="$1"
  local checksum_file="${build_dir}/SHA256SUMS.txt"

  log_info "Computing SHA256 checksums..."

  # Remove previous checksum file if present
  rm -f "${checksum_file}"

  local count=0
  while IFS= read -r -d '' file; do
    local filename sha
    filename="$(basename "${file}")"
    sha="$(sha256sum "${file}" | cut -d' ' -f1)"
    printf '%s  %s\n' "${sha}" "${filename}" >> "${checksum_file}"
    (( count++ )) || true
  done < <(find "${build_dir}" -maxdepth 1 -type f \( -name '*.whl' -o -name '*.tar.gz' \) -print0)

  if [[ -f "${checksum_file}" ]]; then
    log_pass "Checksums written to ${checksum_file} (${count} files)"
  else
    log_warn "No files to checksum"
  fi
}

list_artifacts() {
  local build_dir="$1"

  printf '\n'
  log_info "Build artifacts:"
  printf '  %s\n' "${build_dir}/"
  while IFS= read -r -d '' file; do
    local size
    size="$(stat --format='%s' "${file}" 2>/dev/null || wc -c < "${file}" | tr -d ' ')"
    local size_str
    if [[ "${size}" -ge 1048576 ]]; then
      size_str="$(printf '%.1f MiB' "$(echo "scale=1; ${size} / 1048576" | bc 2>/dev/null || echo "${size}")")"
    elif [[ "${size}" -ge 1024 ]]; then
      size_str="$(printf '%.1f KiB' "$(echo "scale=1; ${size} / 1024" | bc 2>/dev/null || echo "${size}")")"
    else
      size_str="${size} B"
    fi
    printf '    %-50s %s\n' "$(basename "${file}")" "${size_str}"
  done < <(find "${build_dir}" -maxdepth 1 -type f \( -name '*.whl' -o -name '*.tar.gz' -o -name 'SHA256SUMS.txt' \) -print0 | sort -z)
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

main() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --help|-h)
        print_usage_and_exit "$0" \
          "Build Python wheel and sdist packages for Beta release." \
          "[--output <dir>] [--skip-clean]" \
          "  0 — Build successful\n  1 — Missing dependency\n  2 — Build failed\n  4 — Cleanup failed"
        ;;
      --output|-o)
        OUTPUT_DIR="$2"
        shift 2
        ;;
      --skip-clean)
        SKIP_CLEAN=true
        shift
        ;;
      *)
        log_error "Unknown option: $1"
        printf 'Usage: %s [--output <dir>] [--skip-clean]\n' "$0"
        exit 1
        ;;
    esac
  done

  # Validate dependencies
  check_commands python3 || exit "${RC_MISSING_DEP}"
  check_command "pip3" || log_warn "pip3 not found — build may still succeed"

  # Check that build module is available
  if ! python3 -c "import build" 2>/dev/null; then
    log_info "Installing build module..."
    pip3 install build 2>&1 || {
      log_error "Failed to install build module"
      exit "${RC_MISSING_DEP}"
    }
  fi

  # Validate project structure
  check_directory "${CLI_DIR}" "cli/" || exit "${RC_INVALID_STATE}"
  check_file_readable "${CLI_DIR}/pyproject.toml" "pyproject.toml" || exit "${RC_INVALID_STATE}"

  local project_version
  project_version="$(get_project_version)"

  log_info "BCS Release Build — v${project_version}"
  log_info "Output directory: ${OUTPUT_DIR}"
  printf '\n'

  # Clean build directory
  clean_build "${OUTPUT_DIR}" || exit $?

  # Build
  BUILD_DIR="$(mktemp -d 2>/dev/null || mktemp -d 2>/dev/null)"
  trap 'rm -rf "${BUILD_DIR}"' EXIT

  build_wheel "${CLI_DIR}" "${OUTPUT_DIR}" || exit $?
  build_sdist "${CLI_DIR}" "${OUTPUT_DIR}" || exit $?

  # Verify
  printf '\n'
  log_info "Verifying build artifacts..."
  verify_artifacts "${OUTPUT_DIR}" || exit $?

  # Checksums
  compute_checksums "${OUTPUT_DIR}"

  # List
  list_artifacts "${OUTPUT_DIR}"

  # Summary
  printf '\n'
  local total_size
  total_size="$(find "${OUTPUT_DIR}" -maxdepth 1 -type f \( -name '*.whl' -o -name '*.tar.gz' \) -exec stat --format='%s' {} + 2>/dev/null | paste -sd+ | bc 2>/dev/null || echo "0")"
  log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  log_info "Build complete — v${project_version}"
  log_info "Total artifact size: ${total_size} bytes"
  log_info "Artifacts: ${OUTPUT_DIR}/"
  log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
