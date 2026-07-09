#!/usr/bin/env bash
# _shared.sh — Shared functions for hardware validation scripts.
#
# Source this file from other scripts with:
#   readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
#   source "${SCRIPT_DIR}/_shared.sh"
#
# Exit codes: does not exit on its own (intended to be sourced).

set -euo pipefail
IFS=$'\n\t'

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

log_info()  { printf '[INFO]  %s\n' "$*" >&2; }
log_warn()  { printf '[WARN]  %s\n' "$*" >&2; }
log_error() { printf '[ERROR] %s\n' "$*" >&2; }

# ---------------------------------------------------------------------------
# JSON helpers
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

json_null_or_string() {
  if [[ -z "$1" ]]; then
    printf 'null'
  else
    json_string "$1"
  fi
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
# Tool detection
# ---------------------------------------------------------------------------

check_tool_version() {
  local tool="$1"
  if ! command -v "${tool}" &>/dev/null; then
    printf 'null'
    return
  fi
  case "${tool}" in
    efibootmgr)
      efibootmgr --version 2>/dev/null | head -1 || printf 'null'
      ;;
    mokutil)
      mokutil --version 2>/dev/null | head -1 || printf 'null'
      ;;
    lsblk)
      lsblk --version 2>/dev/null | head -1 || printf 'null'
      ;;
    blkid)
      blkid --version 2>/dev/null | head -1 || printf 'null'
      ;;
    findmnt)
      findmnt --version 2>/dev/null | head -1 || printf 'null'
      ;;
    df)
      df --version 2>/dev/null | head -1 || printf 'null'
      ;;
    ip)
      ip --version 2>/dev/null 2>&1 | head -1 || printf 'null'
      ;;
    dmidecode)
      dmidecode --version 2>/dev/null | head -1 || printf 'null'
      ;;
    lsusb)
      lsusb --version 2>/dev/null | head -1 || printf 'null'
      ;;
    nproc)
      nproc --version 2>/dev/null | head -1 || printf 'null'
      ;;
    *)
      "${tool}" --version 2>/dev/null | head -1 || printf 'null'
      ;;
  esac
}

tool_available() {
  command -v "$1" &>/dev/null
}

# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

emit_json_object_start() {
  printf '{\n'
}

emit_json_object_end() {
  printf '\n}\n'
}

emit_json_field() {
  local key="$1"
  local value="$2"
  printf '  %s: %s,\n' "$(json_string "${key}")" "${value}"
}

emit_json_field_last() {
  local key="$1"
  local value="$2"
  printf '  %s: %s\n' "$(json_string "${key}")" "${value}"
}

emit_json_array_start() {
  local indent="${1:-    }"
  printf '%s[\n' "${indent}"
}

emit_json_array_end() {
  local indent="${1:-    }"
  printf '%s]\n' "${indent}"
}

# ---------------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------------

read_sysfs_file() {
  local path="$1"
  if [[ -f "${path}" ]]; then
    cat "${path}" 2>/dev/null || echo ""
  else
    echo ""
  fi
}

read_sysfs_dir_list() {
  local path="$1"
  if [[ -d "${path}" ]]; then
    ls -1 "${path}" 2>/dev/null || true
  fi
}

# ---------------------------------------------------------------------------
# Default output path
# ---------------------------------------------------------------------------

get_default_output_dir() {
  local machine_name="${HOSTNAME:-unknown}"
  local timestamp
  timestamp="$(date --iso-8601=seconds 2>/dev/null || date -u +'%Y-%m-%dT%H:%M:%SZ')"
  local safe_ts="${timestamp//:/-}"
  printf 'hardware-validation/%s/%s' "${machine_name}" "${safe_ts}"
}
