#!/usr/bin/env bash
# collect-artifacts.sh — Gather all Beta validation reports into one
# timestamped archive directory.
#
# Usage:
#   ./scripts/collect-artifacts.sh                    # archive reports/validation/
#   ./scripts/collect-artifacts.sh /path/to/reports    # archive custom directory
#
# The archive is created under reports/archives/ (or
# /path/to/reports/../archives/) with a name like:
#   bcs-beta-validation_2026-07-09T15-30-00+02:00/
#
# Exit codes: 0 on success, 1 on failure.

set -euo pipefail
IFS=$'\n\t'

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------

log_info()  { printf '[INFO]  %s\n' "$*" >&2; }
log_error() { printf '[ERROR] %s\n' "$*" >&2; }

sanitize_timestamp() {
  # Replace colons with hyphens for filesystem safety.
  local ts="$1"
  ts="${ts//:/-}"
  printf '%s' "${ts}"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

main() {
  # Determine source directory.
  local source_dir="${1:-${PROJECT_ROOT}/reports/validation}"

  if [[ ! -d "${source_dir}" ]]; then
    log_error "Source directory not found: ${source_dir}"
    log_error "Run validate-beta.sh first to generate reports."
    exit 1
  fi

  # Verify the source directory contains expected files.
  local file_count
  file_count="$(find "${source_dir}" -maxdepth 1 -type f | wc -l)"
  if [[ "${file_count}" -eq 0 ]]; then
    log_error "Source directory is empty: ${source_dir}"
    exit 1
  fi

  # Determine archives directory (sibling of source).
  local archives_dir
  archives_dir="$(cd "${source_dir}/.." && pwd)/archives"
  mkdir -p "${archives_dir}"

  # Build timestamped archive name.
  local timestamp
  timestamp="$(date --iso-8601=seconds 2>/dev/null || date -u +'%Y-%m-%dT%H:%M:%SZ')"
  local safe_ts
  safe_ts="$(sanitize_timestamp "${timestamp}")"
  local archive_name="bcs-beta-validation_${safe_ts}"
  local archive_path="${archives_dir}/${archive_name}"

  # Copy files into the archive directory.
  mkdir -p "${archive_path}"

  local count=0
  while IFS= read -r -d '' file; do
    cp "${file}" "${archive_path}/"
    (( count++ )) || true
  done < <(find "${source_dir}" -maxdepth 1 -type f -print0)

  # Also copy validation README if present.
  if [[ -f "${source_dir}/README.md" ]]; then
    cp "${source_dir}/README.md" "${archive_path}/README.md"
    (( count++ )) || true
  fi

  log_info "Archived ${count} files to ${archive_path}/"
  log_info "Archive ready: ${archive_path}/"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
