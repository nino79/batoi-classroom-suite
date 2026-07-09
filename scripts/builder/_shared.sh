#!/usr/bin/env bash
# _shared.sh — Shared functions for Builder development helper scripts.
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
# Paths
# ---------------------------------------------------------------------------

# Default constants — scripts that source _shared.sh can override these
# before calling build-stage functions.

: "${BCS_REPO_ROOT:="$(cd "${SCRIPT_DIR}/../.." && pwd)"}"
: "${DEFAULT_WORKSPACE_PREFIX:=".bcs-build"}"

# ---------------------------------------------------------------------------
# Workspace helpers
# ---------------------------------------------------------------------------

# Check whether a path looks like a valid Builder workspace.
# Returns 0 if the path contains the expected subdirectory structure.
is_valid_workspace() {
  local ws="$1"
  [[ -d "${ws}/manifests" && -d "${ws}/metadata" && -d "${ws}/boot" && -d "${ws}/artifacts" ]]
}

# Print the workspace version identifier from metadata/VERSION.
read_workspace_version() {
  local ws="$1"
  if [[ -f "${ws}/metadata/VERSION" ]]; then
    cat "${ws}/metadata/VERSION"
  else
    return 1
  fi
}

# Print the provenance JSON path if it exists.
provenance_path() {
  local ws="$1"
  if [[ -f "${ws}/metadata/provenance.json" ]]; then
    printf '%s' "${ws}/metadata/provenance.json"
  else
    return 1
  fi
}

# ---------------------------------------------------------------------------
# Manifest helpers
# ---------------------------------------------------------------------------

# Validate that a YAML file exists and is parseable (uses Python 3 yaml).
validate_yaml() {
  local file="$1"
  if [[ ! -f "${file}" ]]; then
    log_error "File not found: ${file}"
    return 1
  fi
  python3 -c "import yaml; yaml.safe_load(open('${file}'))" 2>/dev/null || {
    log_error "Invalid YAML: ${file}"
    return 1
  }
}

# Read a specific key from a YAML file using Python.
read_yaml_key() {
  local file="$1"
  local key="$2"
  python3 -c "
import yaml, sys
data = yaml.safe_load(open('${file}'))
keys = '${key}'.split('.')
val = data
for k in keys:
    val = val.get(k, {})
    if val is None:
        break
print(val)
"
}

# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------

# Compute SHA256 checksum of a file.
sha256_file() {
  local file="$1"
  if command -v sha256sum &>/dev/null; then
    sha256sum "${file}" | cut -d' ' -f1
  elif command -v shasum &>/dev/null; then
    shasum -a 256 "${file}" | cut -d' ' -f1
  else
    log_error "No SHA256 tool found"
    return 1
  fi
}

# Recursively list files in a directory with their sizes (human-readable).
list_files_with_sizes() {
  local dir="$1"
  if command -v du &>/dev/null; then
    du -sh "${dir}"/* 2>/dev/null
  else
    find "${dir}" -type f -exec ls -lh {} \; 2>/dev/null
  fi
}

# ---------------------------------------------------------------------------
# JSON helpers (minimal — mirrors hardware-validation/_shared.sh)
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

# ---------------------------------------------------------------------------
# Invocation guard (this file is meant to be sourced, not executed)
# ---------------------------------------------------------------------------

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  log_error "This script is meant to be sourced, not executed directly."
  exit 1
fi
