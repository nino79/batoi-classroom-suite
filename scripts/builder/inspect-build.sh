#!/usr/bin/env bash
# inspect-build.sh — Print a human-readable summary of a completed Builder workspace.
#
# Usage:
#   ./scripts/builder/inspect-build.sh <workspace-dir>
#   ./scripts/builder/inspect-build.sh --json <workspace-dir>
#   ./scripts/builder/inspect-build.sh --checksums <workspace-dir>
#
# Exit codes: 0 on success, 1 if workspace is invalid or missing.

set -euo pipefail
IFS=$'\n\t'

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/_shared.sh"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OUTPUT_MODE="text"
SHOW_CHECKSUMS=false
WORKSPACE=""

# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------

usage() {
  cat >&2 <<EOF
Usage: $(basename "$0") [OPTIONS] <workspace-dir>

Inspect a completed Builder workspace and print a summary.

Options:
  --json         Output as JSON
  --checksums    Include file checksums in output
  -h, --help     Show this help message
EOF
}

inspect_json() {
  local ws="$1"
  local version=""
  local provenance_json="{}"

  version="$(read_workspace_version "${ws}" 2>/dev/null || echo "unknown")"
  provenance_path=$(provenance_path "${ws}" 2>/dev/null || true)
  if [[ -n "${provenance_path}" && -f "${provenance_path}" ]]; then
    provenance_json=$(cat "${provenance_path}")
  fi

  local artifact_count=0
  if [[ -d "${ws}/artifacts" ]]; then
    artifact_count=$(find "${ws}/artifacts" -type f 2>/dev/null | wc -l)
  fi

  local manifest_count=0
  if [[ -d "${ws}/manifests" ]]; then
    manifest_count=$(find "${ws}/manifests" -type f 2>/dev/null | wc -l)
  fi

  local total_size=""
  total_size=$(du -sh "${ws}" 2>/dev/null | cut -f1 || echo "?")

  cat <<JSON
{
  "workspace": $(json_string "${ws}"),
  "valid": true,
  "version": $(json_string "${version}"),
  "total_size": $(json_string "${total_size}"),
  "artifact_count": ${artifact_count},
  "manifest_count": ${manifest_count},
  "has_boot_resources": $( [[ -d "${ws}/boot" && $(find "${ws}/boot" -type f 2>/dev/null | wc -l) -gt 0 ]] && echo true || echo false ),
  "has_metadata": $( [[ -f "${ws}/metadata/provenance.json" ]] && echo true || echo false ),
  "provenance": ${provenance_json}
}
JSON
}

inspect_text() {
  local ws="$1"

  if ! is_valid_workspace "${ws}"; then
    log_error "Not a valid Builder workspace: ${ws}"
    log_error "Expected subdirectories: manifests/, metadata/, boot/, artifacts/"
    return 1
  fi

  local version
  version="$(read_workspace_version "${ws}" 2>/dev/null || echo "unknown")"

  echo "=========================================="
  echo " Builder Workspace Inspection"
  echo "=========================================="
  echo ""
  echo "  Workspace : ${ws}"
  echo "  Version   : ${version}"
  echo ""

  # Artifacts
  echo "--- Artifacts ---"
  if [[ -d "${ws}/artifacts" ]]; then
    local afiles
    afiles=$(find "${ws}/artifacts" -type f 2>/dev/null)
    if [[ -z "${afiles}" ]]; then
      echo "  (empty)"
    else
      list_files_with_sizes "${ws}/artifacts"
    fi
  else
    echo "  (missing)"
  fi
  echo ""

  # Manifests
  echo "--- Manifests ---"
  if [[ -d "${ws}/manifests" ]]; then
    for m in "${ws}/manifests"/*.yaml; do
      if [[ -f "${m}" ]]; then
        local name
        name=$(basename "${m}")
        if validate_yaml "${m}" &>/dev/null; then
          echo "  ${name} : valid YAML"
        else
          echo "  ${name} : INVALID YAML"
        fi
      fi
    done
  else
    echo "  (missing)"
  fi
  echo ""

  # Boot resources
  echo "--- Boot Resources ---"
  if [[ -d "${ws}/boot" ]]; then
    local bfiles
    bfiles=$(find "${ws}/boot" -type f 2>/dev/null)
    if [[ -z "${bfiles}" ]]; then
      echo "  (empty)"
    else
      list_files_with_sizes "${ws}/boot"
    fi
  else
    echo "  (missing)"
  fi
  echo ""

  # Metadata
  echo "--- Metadata ---"
  local p_path
  p_path="$(provenance_path "${ws}" 2>/dev/null || true)"
  if [[ -n "${p_path}" ]]; then
    echo "  provenance.json : present"
    if ${SHOW_CHECKSUMS}; then
      local chk
      chk=$(sha256_file "${p_path}")
      echo "  sha256          : ${chk}"
    fi
  else
    echo "  provenance.json : missing"
  fi
  if [[ -f "${ws}/metadata/build.log" ]]; then
    echo "  build.log       : present ($(wc -l < "${ws}/metadata/build.log") lines)"
  fi
  echo ""

  # Checksums
  if ${SHOW_CHECKSUMS} && [[ -f "${ws}/metadata/checksums.sha256" ]]; then
    echo "--- Checksums ---"
    cat "${ws}/metadata/checksums.sha256"
    echo ""
  fi

  # Summary
  echo "--- Disk Usage ---"
  du -sh "${ws}" 2>/dev/null || echo "  (unknown)"
  echo ""

  if is_valid_workspace "${ws}"; then
    echo "  Status: VALID WORKSPACE"
  fi
}

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------

while [[ $# -gt 0 ]]; do
  case "$1" in
    --json)
      OUTPUT_MODE="json"
      shift
      ;;
    --checksums)
      SHOW_CHECKSUMS=true
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

if [[ ! -d "${WORKSPACE}" ]]; then
  log_error "Workspace directory does not exist: ${WORKSPACE}"
  exit 1
fi

case "${OUTPUT_MODE}" in
  json)
    inspect_json "${WORKSPACE}"
    ;;
  text)
    inspect_text "${WORKSPACE}"
    ;;
esac
