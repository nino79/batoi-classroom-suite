#!/usr/bin/env bash
# clean-workspace.sh — Remove Builder workspace directories.
#
# Usage:
#   ./scripts/builder/clean-workspace.sh                    # remove .bcs-build-* in CWD
#   ./scripts/builder/clean-workspace.sh --all              # remove .bcs-build-* and _bcs-build-*
#   ./scripts/builder/clean-workspace.sh /path/to/workspace # remove specific directory
#   ./scripts/builder/clean-workspace.sh --dry-run          # print what would be removed
#
# Exit codes: 0 on success, 1 on error.

set -euo pipefail
IFS=$'\n\t'

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/_shared.sh"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DRY_RUN=false
REMOVE_ALL=false
TARGETS=()

# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------

usage() {
  cat >&2 <<EOF
Usage: $(basename "$0") [OPTIONS] [TARGET...]

Remove Builder workspace directories.

Options:
  --all       Remove both .bcs-build-* and _bcs-build-* directories
  --dry-run   Print what would be removed without removing
  -h, --help  Show this help message

If no TARGET is given, remove .bcs-build-* in the current directory.
EOF
}

remove_workspace() {
  local dir="$1"
  if [[ ! -d "${dir}" ]]; then
    log_warn "Not a directory or does not exist: ${dir}"
    return
  fi
  if ${DRY_RUN}; then
    log_info "Would remove: ${dir}"
  else
    rm -rf "${dir}"
    log_info "Removed: ${dir}"
  fi
}

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------

while [[ $# -gt 0 ]]; do
  case "$1" in
    --all)
      REMOVE_ALL=true
      shift
      ;;
    --dry-run)
      DRY_RUN=true
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
      TARGETS+=("$1")
      shift
      ;;
  esac
done

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if [[ ${#TARGETS[@]} -gt 0 ]]; then
  # Remove specific targets
  for t in "${TARGETS[@]}"; do
    remove_workspace "${t}"
  done
elif ${REMOVE_ALL}; then
  # Remove both patterns
  log_info "Scanning for .bcs-build-* and _bcs-build-* directories in $(pwd)..."
  while IFS= read -r -d '' d; do
    remove_workspace "${d}"
  done < <(find . -maxdepth 1 -type d \( -name '.bcs-build-*' -o -name '_bcs-build-*' \) -print0 2>/dev/null || true)
else
  # Remove default pattern only
  log_info "Scanning for .bcs-build-* directories in $(pwd)..."
  while IFS= read -r -d '' d; do
    remove_workspace "${d}"
  done < <(find . -maxdepth 1 -type d -name '.bcs-build-*' -print0 2>/dev/null || true)
fi

log_info "Done."
