#!/usr/bin/env bash
# _shared.sh — Shared functions for Beta diagnostics dashboard scripts.
#
# Source this file from other scripts with:
#   readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
#   source "${SCRIPT_DIR}/_shared.sh"

set -euo pipefail
IFS=$'\n\t'

# ---------------------------------------------------------------------------
# Repository layout
# ---------------------------------------------------------------------------

readonly SCRIPT_DIR_REAL="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "${SCRIPT_DIR_REAL}/../.." && pwd)"
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
readonly RC_COLLECT_FAILED=2
readonly RC_BUILD_FAILED=3
readonly RC_VALIDATE_FAILED=4

# ---------------------------------------------------------------------------
# JSON helpers (inline — no python3 required for simple values)
# ---------------------------------------------------------------------------

json_string() {
  local value="$1"
  value="${value//\\/\\\\}"
  value="${value//\"/\\\"}"
  value="${value//$'\n'/\\n}"
  value="${value//$'\t'/\\t}"
  value="${value//$'\r'/\\r}"
  printf '"%s"' "${value}"
}

json_int() {
  printf '%d' "$1"
}

json_bool() {
  if [[ "$1" == "true" || "$1" == "1" ]]; then
    printf 'true'
  else
    printf 'false'
  fi
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

check_command() {
  local cmd="$1"
  if ! command -v "${cmd}" &>/dev/null; then
    log_error "Required command not found: ${cmd}"
    return 1
  fi
}

check_directory() {
  local path="$1"
  local label="${2:-directory}"
  if [[ -d "${path}" ]]; then
    return 0
  fi
  return 1
}

check_file() {
  local path="$1"
  if [[ -f "${path}" ]]; then
    return 0
  fi
  return 1
}

safe_read_file() {
  local path="$1"
  local default="${2:-}"
  if [[ -f "${path}" && -r "${path}" ]]; then
    cat "${path}" 2>/dev/null || printf '%s' "${default}"
  else
    printf '%s' "${default}"
  fi
}

count_files() {
  local pattern="$1"
  local dir="$2"
  if [[ -d "${dir}" ]]; then
    find "${dir}" -maxdepth 1 -type f -name "${pattern}" 2>/dev/null | wc -l
  else
    printf '0'
  fi
}

# ---------------------------------------------------------------------------
# Markdown helpers
# ---------------------------------------------------------------------------

md_table_header() {
  local -a headers=("$@")
  local sep=""
  printf '|'
  for h in "${headers[@]}"; do
    printf ' %s |' "${h}"
  done
  printf '\n|'
  for _ in "${headers[@]}"; do
    printf ' --- |'
  done
  printf '\n'
}

md_table_row() {
  local -a cells=("$@")
  printf '|'
  for c in "${cells[@]}"; do
    printf ' %s |' "${c}"
  done
  printf '\n'
}

md_badge() {
  local label="$1"
  local value="$2"
  local color="$3"
  printf '![%s](https://img.shields.io/badge/%s-%s-%s)\n' "${label}" "${label}" "${value}" "${color}"
}
