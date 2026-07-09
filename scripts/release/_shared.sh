#!/usr/bin/env bash
# _shared.sh — Shared functions for release engineering scripts.
#
# Source this file from other scripts with:
#   readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
#   source "${SCRIPT_DIR}/_shared.sh"
#
# Exit codes: does not exit on its own (intended to be sourced).

set -euo pipefail
IFS=$'\n\t'

# ---------------------------------------------------------------------------
# Repository layout
# ---------------------------------------------------------------------------

readonly PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
readonly CLI_DIR="${PROJECT_ROOT}/cli"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

log_info()  { printf '[INFO]  %s\n' "$*" >&2; }
log_warn()  { printf '[WARN]  %s\n' "$*" >&2; }
log_error() { printf '[ERROR] %s\n' "$*" >&2; }
log_pass()  { printf '[PASS]  %s\n' "$*" >&2; }
log_fail()  { printf '[FAIL]  %s\n' "$*" >&2; }

# ---------------------------------------------------------------------------
# Exit codes
# ---------------------------------------------------------------------------

readonly RC_OK=0
readonly RC_MISSING_DEP=1
readonly RC_BUILD_FAILED=2
readonly RC_VERIFY_FAILED=3
readonly RC_CLEANUP_FAILED=4
readonly RC_INVALID_STATE=5

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

print_usage_and_exit() {
  local script_name="$1"
  local description="$2"
  local usage="$3"
  local exit_codes="${4:-}"

  printf '%s\n\n' "${description}"
  printf 'Usage:\n  %s %s\n\n' "${script_name}" "${usage}"
  printf 'Options:\n  --help, -h    Print this help message and exit\n'

  if [[ -n "${exit_codes}" ]]; then
    printf '\nExit codes:\n%s\n' "${exit_codes}"
  fi

  exit "${RC_OK}"
}

check_command() {
  local cmd="$1"
  if ! command -v "${cmd}" &>/dev/null; then
    log_error "Required command not found: ${cmd}"
    return 1
  fi
}

check_commands() {
  local missing=0
  for cmd in "$@"; do
    if ! command -v "${cmd}" &>/dev/null; then
      log_error "Required command not found: ${cmd}"
      (( missing++ )) || true
    fi
  done
  if [[ "${missing}" -gt 0 ]]; then
    log_error "${missing} required command(s) missing — install them and retry"
    return 1
  fi
}

check_file_readable() {
  local path="$1"
  local label="${2:-file}"
  if [[ ! -f "${path}" ]]; then
    log_error "${label} not found: ${path}"
    return 1
  fi
  if [[ ! -r "${path}" ]]; then
    log_error "${label} not readable: ${path}"
    return 1
  fi
}

check_directory() {
  local path="$1"
  local label="${2:-directory}"
  if [[ ! -d "${path}" ]]; then
    log_error "${label} not found: ${path}"
    return 1
  fi
}

# ---------------------------------------------------------------------------
# Project metadata helpers
# ---------------------------------------------------------------------------

get_project_version() {
  if [[ -f "${PROJECT_ROOT}/VERSION" ]]; then
    cat "${PROJECT_ROOT}/VERSION"
  else
    echo "0.0.0"
  fi
}

get_project_name() {
  # Read from pyproject.toml
  if [[ -f "${CLI_DIR}/pyproject.toml" ]]; then
    grep -oP '(?<=^name = ").*(?=")' "${CLI_DIR}/pyproject.toml" 2>/dev/null || echo "bcs"
  else
    echo "bcs"
  fi
}

# ---------------------------------------------------------------------------
# Virtual environment helpers
# ---------------------------------------------------------------------------

create_venv() {
  local venv_path="$1"
  if [[ -d "${venv_path}" ]]; then
    log_warn "Virtual environment already exists: ${venv_path}"
    return 0
  fi
  python3 -m venv "${venv_path}" 2>/dev/null || {
    log_error "Failed to create virtual environment at ${venv_path}"
    return 1
  }
  log_info "Virtual environment created at ${venv_path}"
}

activate_venv() {
  local venv_path="$1"
  local activate="${venv_path}/bin/activate"
  if [[ ! -f "${activate}" ]]; then
    log_error "Cannot activate virtual environment — missing: ${activate}"
    return 1
  fi
  # shellcheck disable=SC1090
  source "${activate}" 2>/dev/null || {
    log_error "Failed to activate virtual environment: ${venv_path}"
    return 1
  }
}

destroy_venv() {
  local venv_path="$1"
  if [[ -d "${venv_path}" ]]; then
    rm -rf "${venv_path}"
    log_info "Virtual environment removed: ${venv_path}"
  fi
}
