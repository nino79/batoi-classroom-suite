#!/usr/bin/env bash
# compare-builds.sh — Compare two Builder workspaces for differences.
#
# Compares manifests, metadata, and file listings between two build
# outputs. Useful for regression checking: "does this change alter the
# build output beyond what was expected?"
#
# Usage:
#   ./scripts/builder/compare-builds.sh <workspace-A> <workspace-B>
#   ./scripts/builder/compare-builds.sh --verbose <workspace-A> <workspace-B>
#   ./scripts/builder/compare-builds.sh --manifests-only <workspace-A> <workspace-B>
#
# Exit codes:
#   0 — identical (within compared scope)
#   1 — differences found
#   2 — one or both workspaces invalid

set -euo pipefail
IFS=$'\n\t'

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/_shared.sh"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

VERBOSE=false
MANIFESTS_ONLY=false
WORKSPACE_A=""
WORKSPACE_B=""
HAS_DIFFS=false

# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------

usage() {
  cat >&2 <<EOF
Usage: $(basename "$0") [OPTIONS] <workspace-A> <workspace-B>

Compare two Builder workspaces for differences.

Options:
  --verbose         Show detailed diff output
  --manifests-only  Only compare manifests/ and metadata/ (skip boot/ and artifacts/)
  -h, --help        Show this help message
EOF
}

compare_files() {
  local label="$1"
  local file_a="$2"
  local file_b="$3"

  if [[ ! -f "${file_a}" ]] && [[ ! -f "${file_b}" ]]; then
    return 0  # both absent — no difference
  fi
  if [[ ! -f "${file_a}" ]]; then
    log_warn "DIFF: ${label} — present in B, absent in A"
    HAS_DIFFS=true
    return 1
  fi
  if [[ ! -f "${file_b}" ]]; then
    log_warn "DIFF: ${label} — present in A, absent in B"
    HAS_DIFFS=true
    return 1
  fi

  if ! diff -q "${file_a}" "${file_b}" &>/dev/null; then
    log_warn "DIFF: ${label} — files differ"
    HAS_DIFFS=true
    if ${VERBOSE}; then
      echo "--- ${label} ---"
      diff -u "${file_a}" "${file_b}" 2>/dev/null || true
      echo ""
    fi
    return 1
  fi

  log_info "OK: ${label} — identical"
  return 0
}

compare_dir_listing() {
  local label="$1"
  local dir_a="$2"
  local dir_b="$3"

  local list_a list_b
  list_a=$(find "${dir_a}" -type f 2>/dev/null | sort)
  list_b=$(find "${dir_b}" -type f 2>/dev/null | sort)

  if [[ "${list_a}" != "${list_b}" ]]; then
    log_warn "DIFF: ${label} — file listing differs"
    HAS_DIFFS=true
    if ${VERBOSE}; then
      diff -u <(echo "${list_a}") <(echo "${list_b}") || true
    fi
    return 1
  fi

  log_info "OK: ${label} — identical file listing"
  return 0
}

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------

while [[ $# -gt 0 ]]; do
  case "$1" in
    --verbose)
      VERBOSE=true
      shift
      ;;
    --manifests-only)
      MANIFESTS_ONLY=true
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
      if [[ -z "${WORKSPACE_A}" ]]; then
        WORKSPACE_A="$1"
      elif [[ -z "${WORKSPACE_B}" ]]; then
        WORKSPACE_B="$1"
      else
        log_error "Too many arguments"
        usage
        exit 1
      fi
      shift
      ;;
  esac
done

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if [[ -z "${WORKSPACE_A}" ]] || [[ -z "${WORKSPACE_B}" ]]; then
  log_error "Two workspace paths are required"
  usage
  exit 1
fi

log_info "Comparing:"
log_info "  A: ${WORKSPACE_A}"
log_info "  B: ${WORKSPACE_B}"

# Validate both workspaces
for ws in "${WORKSPACE_A}" "${WORKSPACE_B}"; do
  if ! is_valid_workspace "${ws}"; then
    log_error "Invalid workspace: ${ws}"
    exit 2
  fi
done

echo ""

# Compare versions
local version_a version_b
version_a=$(read_workspace_version "${WORKSPACE_A}" 2>/dev/null || echo "unknown")
version_b=$(read_workspace_version "${WORKSPACE_B}" 2>/dev/null || echo "unknown")
if [[ "${version_a}" != "${version_b}" ]]; then
  log_warn "DIFF: version — A=${version_a}, B=${version_b}"
  HAS_DIFFS=true
else
  log_info "OK: version — ${version_a}"
fi

echo ""

# Compare manifests
compare_dir_listing "manifests/ file listing" \
  "${WORKSPACE_A}/manifests" "${WORKSPACE_B}/manifests"

for f in packages.yaml layout.yaml boot-entries.yaml; do
  compare_files "manifests/${f}" \
    "${WORKSPACE_A}/manifests/${f}" \
    "${WORKSPACE_B}/manifests/${f}"
done

echo ""

# Compare metadata (skip provenance fields that change every build)
compare_files "metadata/VERSION" \
  "${WORKSPACE_A}/metadata/VERSION" \
  "${WORKSPACE_B}/metadata/VERSION"

# For provenance.json, only compare structural fields (not timestamps)
if [[ -f "${WORKSPACE_A}/metadata/provenance.json" && -f "${WORKSPACE_B}/metadata/provenance.json" ]]; then
  local stripped_a stripped_b
  stripped_a=$(python3 -c "
import json
d = json.load(open('${WORKSPACE_A}/metadata/provenance.json'))
d.get('build', {}).pop('timestamp', None)
d.get('build', {}).pop('duration_seconds', None)
print(json.dumps(d, sort_keys=True))
" 2>/dev/null || echo "ERROR")
  stripped_b=$(python3 -c "
import json
d = json.load(open('${WORKSPACE_B}/metadata/provenance.json'))
d.get('build', {}).pop('timestamp', None)
d.get('build', {}).pop('duration_seconds', None)
print(json.dumps(d, sort_keys=True))
" 2>/dev/null || echo "ERROR")

  if [[ "${stripped_a}" == "ERROR" || "${stripped_b}" == "ERROR" ]]; then
    log_error "Could not parse provenance.json in one or both workspaces"
    HAS_DIFFS=true
  elif [[ "${stripped_a}" != "${stripped_b}" ]]; then
    log_warn "DIFF: metadata/provenance.json (ignoring build.timestamp, build.duration_seconds)"
    HAS_DIFFS=true
    if ${VERBOSE}; then
      diff -u <(echo "${stripped_a}") <(echo "${stripped_b}") || true
    fi
  else
    log_info "OK: metadata/provenance.json — identical (ignoring timestamps)"
  fi
fi

if ! ${MANIFESTS_ONLY}; then
  echo ""

  # Compare boot resources
  compare_dir_listing "boot/ file listing" \
    "${WORKSPACE_A}/boot" "${WORKSPACE_B}/boot"

  # Compare artifacts file listing (not raw binary content — images will always differ)
  compare_dir_listing "artifacts/ file listing" \
    "${WORKSPACE_A}/artifacts" "${WORKSPACE_B}/artifacts"
fi

echo ""

# Final result
if ${HAS_DIFFS}; then
  log_warn "Comparison complete — differences found."
  exit 1
else
  log_info "Comparison complete — workspaces are identical (within compared scope)."
  exit 0
fi
