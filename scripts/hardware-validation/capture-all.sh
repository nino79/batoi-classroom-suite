#!/usr/bin/env bash
# capture-all.sh — Orchestrate all hardware validation captures.
#
# Runs every capture-*.sh script in sequence and writes output to a
# timestamped directory structure:
#   hardware-validation/<machine-name>/<timestamp>/
#     system.json, system-summary.md
#     storage.json, storage-summary.md
#     network.json, network-summary.md
#     firmware.json, firmware-summary.md
#     usb.json, usb-summary.md
#     summary.md
#
# Usage:
#   ./scripts/hardware-validation/capture-all.sh
#   ./scripts/hardware-validation/capture-all.sh --dir /path/to/output
#   ./scripts/hardware-validation/capture-all.sh --human-only
#
# Exit codes:
#   0 — All captures completed (individual failures recorded in summary).
#   1 — Fatal error (e.g. missing dependency).
#   2 — No capture scripts found.

set -euo pipefail
IFS=$'\n\t'

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/_shared.sh"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OUTPUT_DIR=""
HUMAN_ONLY=false

# Define the capture scripts to run (order matters for summary).
declare -a CAPTURE_SCRIPTS=(
  "system"
  "storage"
  "network"
  "firmware"
  "usb"
)

# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------

get_default_output_dir() {
  local machine_name="${HOSTNAME:-unknown}"
  local timestamp
  timestamp="$(date --iso-8601=seconds 2>/dev/null || date -u +'%Y-%m-%dT%H:%M:%SZ')"
  local safe_ts="${timestamp//:/-}"
  printf 'hardware-validation/%s/%s' "${machine_name}" "${safe_ts}"
}

write_summary() {
  local output_dir="$1"
  shift
  # Remaining args: capturer_name|exit_code|duration pairs
  local -a results=("$@")
  local machine_name="${HOSTNAME:-unknown}"
  local timestamp
  timestamp="$(date --iso-8601=seconds 2>/dev/null || date -u +'%Y-%m-%dT%H:%M:%SZ')"

  local total=$#
  local passed=0 failed=0
  for entry in "${results[@]}"; do
    local rc
    IFS='|' read -r _ rc _ <<< "${entry}"
    if [[ "${rc}" -eq 0 ]]; then
      (( passed++ )) || true
    else
      (( failed++ )) || true
    fi
  done

  {
    printf '# Hardware Validation Capture\n\n'
    printf '**Machine:** %s  \n' "${machine_name}"
    printf '**Date:** %s  \n' "${timestamp}"
    printf '**Result:** %d/%d passed, %d failed  \n\n' "${passed}" "${total}" "${failed}"
    printf '## Capture Results\n\n'
    printf '| Domain | Exit Code | Duration |\n'
    printf '|---|---|---|\n'
    for entry in "${results[@]}"; do
      local name rc dur
      IFS='|' read -r name rc dur <<< "${entry}"
      local icon="✅"
      if [[ "${rc}" -ne 0 ]]; then
        icon="❌"
      fi
      printf '| %s %s | %d | %ss |\n' "${icon}" "${name}" "${rc}" "${dur}"
    done
    printf '\n## Files\n\n'
    printf '| File | Description |\n'
    printf '|---|---|\n'
    printf '| system.json | Kernel, distribution, CPU, memory, DMI, hypervisor, tools |\n'
    printf '| storage.json | Block devices, partitions, filesystems, mountpoints |\n'
    printf '| network.json | Network interfaces, MAC, state, IP addresses |\n'
    printf '| firmware.json | UEFI mode, Secure Boot, boot entries, DMI firmware |\n'
    printf '| usb.json | USB controllers, devices, removable storage |\n'
    printf '| system-summary.md | Human-readable system summary |\n'
    printf '| storage-summary.md | Human-readable storage summary |\n'
    printf '| network-summary.md | Human-readable network summary |\n'
    printf '| firmware-summary.md | Human-readable firmware summary |\n'
    printf '| usb-summary.md | Human-readable USB summary |\n'
    printf '| summary.md | This file — overall capture results |\n'
  } > "${output_dir}/summary.md"
}

now_epoch() {
  if tool_available python3; then
    python3 -c "import time; print(time.time())" 2>/dev/null || printf '%s' "$(date +%s)"
  else
    date +%s
  fi
}

duration_seconds() {
  local start_sec="$1"
  local end_sec="$2"
  if tool_available python3; then
    python3 -c "print(round(float('${end_sec}') - float('${start_sec}'), 3))" 2>/dev/null || printf '%d' $(( end_sec - start_sec ))
  else
    printf '%d' $(( end_sec - start_sec ))
  fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

main() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --dir)
        OUTPUT_DIR="$2"
        shift 2
        ;;
      --human-only)
        HUMAN_ONLY=true
        shift
        ;;
      *)
        log_error "Unknown option: $1"
        printf 'Usage: %s [--dir <path>] [--human-only]\n' "$0"
        exit 1
        ;;
    esac
  done

  # Determine output directory.
  if [[ -z "${OUTPUT_DIR}" ]]; then
    OUTPUT_DIR="$(get_default_output_dir)"
  fi
  mkdir -p "${OUTPUT_DIR}"

  log_info "Output directory: ${OUTPUT_DIR}/"
  log_info "Starting hardware validation capture — $(date)"

  local start_time
  start_time="$(now_epoch)"
  local overall_rc=0
  declare -a results

  for domain in "${CAPTURE_SCRIPTS[@]}"; do
    local script="${SCRIPT_DIR}/capture-${domain}.sh"
    local capture_start capture_end duration
    capture_start="$(now_epoch)"

    if [[ ! -f "${script}" ]]; then
      log_error "Capture script not found: ${script}"
      results+=("${domain}|1|0")
      overall_rc=1
      continue
    fi

    log_info "Capturing ${domain}…"

    set +e
    if [[ "${HUMAN_ONLY}" == true ]]; then
      bash "${script}" --human > "${OUTPUT_DIR}/${domain}-summary.md" 2>&1
    else
      bash "${script}" > "${OUTPUT_DIR}/${domain}.json" 2>"${OUTPUT_DIR}/${domain}-stderr.txt"
      bash "${script}" --human > "${OUTPUT_DIR}/${domain}-summary.md" 2>/dev/null
    fi
    local rc=$?
    set -e

    capture_end="$(now_epoch)"
    duration="$(duration_seconds "${capture_start}" "${capture_end}")"
    results+=("${domain}|${rc}|${duration}")

    if [[ "${rc}" -eq 0 ]]; then
      log_info "  ${domain} — OK (${duration}s)"
    else
      log_warn "  ${domain} — FAILED (exit ${rc}, ${duration}s)"
      overall_rc=1
    fi
  done

  # Write summary
  write_summary "${OUTPUT_DIR}" "${results[@]}"
  log_info "Summary written to ${OUTPUT_DIR}/summary.md"

  local end_time total_duration
  end_time="$(now_epoch)"
  total_duration="$(duration_seconds "${start_time}" "${end_time}")"

  local total=${#results[@]}
  local passed=0 failed=0
  for entry in "${results[@]}"; do
    local rc
    IFS='|' read -r _ rc _ <<< "${entry}"
    if [[ "${rc}" -eq 0 ]]; then
      (( passed++ )) || true
    else
      (( failed++ )) || true
    fi
  done

  printf '\n'
  log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  log_info "Capture complete — ${passed}/${total} passed, ${failed} failed"
  log_info "Total time: ${total_duration}s"
  log_info "Output: ${OUTPUT_DIR}/"
  log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  exit "${overall_rc}"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
