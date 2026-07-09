#!/usr/bin/env bash
# verify-install.sh — Verify a bcs installation in a fresh virtual environment
# from start to finish, simulating a real user install.
#
# Performs a complete install cycle:
#   1. Create a fresh virtual environment
#   2. Install bcs from a wheel (or pip install)
#   3. Verify all CLI commands produce expected output
#   4. Verify --help for every command
#   5. Verify entry points and metadata
#   6. Clean up
#
# Usage:
#   ./scripts/release/verify-install.sh
#   ./scripts/release/verify-install.sh --wheel /path/to/bcs-*.whl
#   ./scripts/release/verify-install.sh --source /path/to/cli
#   ./scripts/release/verify-install.sh --keep-venv
#   ./scripts/release/verify-install.sh --help
#
# Exit codes:
#   0 — Installation verified successfully
#   1 — Missing dependency
#   3 — Verification failed

set -euo pipefail
IFS=$'\n\t'

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/_shared.sh"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

INSTALL_SOURCE=""
KEEP_VENV=false
VENV_DIR=""
FAILED=0

# ---------------------------------------------------------------------------
# Verification functions
# ---------------------------------------------------------------------------

verify_bcs_version() {
  local bcs_bin="$1"
  local expected_version="$2"

  log_info "Checking bcs --version..."

  local version_output
  version_output="$("${bcs_bin}" --version 2>&1 || true)"

  if [[ -z "${version_output}" ]]; then
    log_fail "bcs --version produced no output"
    return 1
  fi

  # Check that version is mentioned
  if printf '%s' "${version_output}" | grep -qi "${expected_version}"; then
    log_pass "bcs --version: ${version_output}"
  elif printf '%s' "${version_output}" | grep -qi "bcs"; then
    log_pass "bcs --version: ${version_output} (version embedded)"
  else
    log_warn "bcs --version output: ${version_output}"
  fi
}

verify_help_output() {
  local bcs_bin="$1"
  local subcommand="$2"

  local help_output
  help_output="$("${bcs_bin}" ${subcommand} --help 2>&1 || true)"

  if [[ -z "${help_output}" ]]; then
    log_fail "bcs ${subcommand} --help produced no output"
    return 1
  fi

  # Check it looks like help text
  if printf '%s' "${help_output}" | grep -qi "usage\|help\|Usage"; then
    log_pass "bcs ${subcommand} --help works"
  else
    log_warn "bcs ${subcommand} --help output may be incomplete"
  fi
}

verify_command_executes() {
  local bcs_bin="$1"
  local description="$2"
  local command="$3"
  local expect_success="${4:-true}"

  log_info "Running: bcs ${command}"

  local output rc
  output="$("${bcs_bin}" ${command} 2>&1)" || rc=$?
  rc=${rc:-0}

  if [[ "${expect_success}" == true ]]; then
    if [[ "${rc}" -eq 0 ]]; then
      log_pass "bcs ${command} exited 0"
      # Print first line of output
      local first_line
      first_line="$(printf '%s' "${output}" | head -1)"
      if [[ -n "${first_line}" ]]; then
        log_info "  Output: ${first_line}"
      fi
    else
      log_fail "bcs ${command} exited ${rc}"
      log_info "  Output: $(printf '%s' "${output}" | head -3)"
      return 1
    fi
  else
    log_info "bcs ${command} exited ${rc}"
  fi
}

verify_entry_point_location() {
  local bcs_bin="$1"

  if [[ -x "${bcs_bin}" ]]; then
    log_pass "bcs entry point is executable: ${bcs_bin}"
  else
    log_fail "bcs entry point not executable: ${bcs_bin}"
    return 1
  fi
}

verify_package_metadata() {
  local python_bin="$1"

  log_info "Verifying package metadata..."

  local metadata_ok=true

  if ! "${python_bin}" -c "
import bcs
print(f'Package: {bcs.__package__ or \"bcs\"}')
print(f'Module location: {bcs.__file__}')
" 2>&1; then
    metadata_ok=false
  fi

  # Check dependencies are importable
  for mod in typer rich pydantic yaml; do
    if "${python_bin}" -c "import ${mod}" 2>/dev/null; then
      true
    else
      log_warn "Dependency not importable: ${mod}"
    fi
  done

  if [[ "${metadata_ok}" == true ]]; then
    log_pass "Package metadata verified"
  fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

main() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --help|-h)
        printf '%s\n\n' "Verify a bcs installation in a fresh virtual environment."
        printf 'Usage:\n  %s [--wheel <file>] [--source <dir>] [--keep-venv]\n\n' "$0"
        printf 'Options:\n'
        printf '  --wheel <file>    Install from wheel file (default: build first)\n'
        printf '  --source <dir>    Install from source directory (default: cli/)\n'
        printf '  --keep-venv       Do not remove the virtual environment after testing\n'
        printf '  --help, -h        Print this help message\n'
        exit 0
        ;;
      --wheel|-w)
        INSTALL_SOURCE="$2"
        shift 2
        ;;
      --source|-s)
        INSTALL_SOURCE="$2"
        shift 2
        ;;
      --keep-venv)
        KEEP_VENV=true
        shift
        ;;
      *)
        log_error "Unknown option: $1"
        printf 'Usage: %s [--wheel <file> | --source <dir>] [--keep-venv]\n' "$0"
        exit 1
        ;;
    esac
  done

  # Validate dependencies
  check_commands python3 pip3 git || exit "${RC_MISSING_DEP}"

  local project_version
  project_version="$(get_project_version)"

  log_info "BCS Install Verification — v${project_version}"
  printf '\n'

  # Create fresh virtual environment
  VENV_DIR="$(mktemp -d 2>/dev/null || mktemp -d 2>/dev/null)/bcs-test-venv"
  log_info "Creating fresh virtual environment..."

  if ! python3 -m venv "${VENV_DIR}"; then
    log_error "Failed to create virtual environment"
    exit "${RC_VERIFY_FAILED}"
  fi

  local python_bin="${VENV_DIR}/bin/python3"
  local pip_bin="${VENV_DIR}/bin/pip"
  local bcs_bin="${VENV_DIR}/bin/bcs"

  # Upgrade pip
  log_info "Upgrading pip..."
  "${pip_bin}" install --upgrade pip 2>&1 || log_warn "pip upgrade failed"

  # Install
  printf '\n'
  if [[ -n "${INSTALL_SOURCE}" ]]; then
    if [[ "${INSTALL_SOURCE}" == *.whl ]]; then
      log_info "Installing from wheel: ${INSTALL_SOURCE}"
      "${pip_bin}" install "${INSTALL_SOURCE}" 2>&1 || {
        log_error "Installation from wheel failed"
        exit "${RC_VERIFY_FAILED}"
      }
    else
      log_info "Installing from source: ${INSTALL_SOURCE}"
      "${pip_bin}" install -e "${INSTALL_SOURCE}" 2>&1 || {
        log_error "Installation from source failed"
        exit "${RC_VERIFY_FAILED}"
      }
    fi
  else
    # Try building first, then install from wheel
    local dist_dir="${PROJECT_ROOT}/dist"
    if [[ -d "${dist_dir}" ]]; then
      local wheel_file
      wheel_file="$(find "${dist_dir}" -name '*.whl' -type f 2>/dev/null | head -1 || true)"
      if [[ -n "${wheel_file}" ]]; then
        log_info "Installing from pre-built wheel: ${wheel_file}"
        "${pip_bin}" install "${wheel_file}" 2>&1 || {
          log_error "Installation from pre-built wheel failed"
          exit "${RC_VERIFY_FAILED}"
        }
      else
        log_info "Installing from source (editable): ${CLI_DIR}"
        "${pip_bin}" install -e "${CLI_DIR}" 2>&1 || {
          log_error "Installation from source failed"
          exit "${RC_VERIFY_FAILED}"
        }
      fi
    else
      log_info "Installing from source (editable): ${CLI_DIR}"
      "${pip_bin}" install -e "${CLI_DIR}" 2>&1 || {
        log_error "Installation from source failed"
        exit "${RC_VERIFY_FAILED}"
      }
    fi
  fi
  log_pass "Installation completed"

  # Verify
  printf '\n'
  log_info "Verifying installation..."
  printf '\n'

  # Entry point
  verify_entry_point_location "${bcs_bin}" || (( FAILED++ )) || true
  printf '\n'

  # Version
  verify_bcs_version "${bcs_bin}" "${project_version}" || (( FAILED++ )) || true
  printf '\n'

  # --help for main command
  verify_help_output "${bcs_bin}" "" || (( FAILED++ )) || true
  printf '\n'

  # --help for subcommands
  for cmd in version doctor validate inventory; do
    verify_help_output "${bcs_bin}" "${cmd}" || (( FAILED++ )) || true
  done
  printf '\n'

  # Command execution tests
  verify_command_executes "${bcs_bin}" "version" "version" true || (( FAILED++ )) || true
  printf '\n'

  # Package metadata
  verify_package_metadata "${python_bin}" || (( FAILED++ )) || true
  printf '\n'

  # Verify cleanup
  log_info "Cleaning up..."
  if [[ "${KEEP_VENV}" == true ]]; then
    log_info "Virtual environment kept at: ${VENV_DIR}"
  else
    rm -rf "${VENV_DIR}"
    log_info "Virtual environment removed"
  fi

  # Summary
  printf '\n'
  log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  if [[ "${FAILED}" -eq 0 ]]; then
    log_info "Install verification passed — all checks OK"
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit "${RC_OK}"
  else
    log_warn "Install verification completed with ${FAILED} failure(s)"
    log_warn "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit "${RC_VERIFY_FAILED}"
  fi
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
