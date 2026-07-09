#!/usr/bin/env bash
# capture-system.sh — Capture system-level hardware and environment metadata.
#
# Outputs JSON to stdout with keys: timestamp, machine_name, kernel,
# distribution, cpu, memory, dmi, hypervisor, tools.
#
# Usage:
#   ./scripts/hardware-validation/capture-system.sh
#   ./scripts/hardware-validation/capture-system.sh --dir /path/to/capture
#   ./scripts/hardware-validation/capture-system.sh --human
#
# Exit codes: 0 on success, 1 on critical failure.

set -euo pipefail
IFS=$'\n\t'

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/_shared.sh"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OUTPUT_DIR=""
HUMAN_ONLY=false

# ---------------------------------------------------------------------------
# Collection functions
# ---------------------------------------------------------------------------

collect_kernel() {
  uname -a 2>/dev/null || echo "unknown"
}

collect_distribution() {
  local id="unknown" version="unknown" pretty="unknown"
  if [[ -f /etc/os-release ]]; then
    id="$(grep -oP '(?<=^ID=).*' /etc/os-release 2>/dev/null | tr -d '"' || echo "unknown")"
    version="$(grep -oP '(?<=^VERSION_ID=).*' /etc/os-release 2>/dev/null | tr -d '"' || echo "unknown")"
    pretty="$(grep -oP '(?<=^PRETTY_NAME=).*' /etc/os-release 2>/dev/null | tr -d '"' || echo "unknown")"
  elif command -v lsb_release &>/dev/null; then
    id="$(lsb_release -si 2>/dev/null | tr '[:upper:]' '[:lower:]' || echo "unknown")"
    version="$(lsb_release -sr 2>/dev/null || echo "unknown")"
    pretty="$(lsb_release -sd 2>/dev/null || echo "unknown")"
  fi
  printf '{"id": %s, "version": %s, "pretty_name": %s}' \
    "$(json_string "${id}")" \
    "$(json_string "${version}")" \
    "$(json_string "${pretty}")"
}

collect_cpu() {
  local model="unknown" cores=0 threads=0 arch
  arch="$(uname -m 2>/dev/null || echo "unknown")"
  if [[ -f /proc/cpuinfo ]]; then
    model="$(grep -m1 'model name' /proc/cpuinfo 2>/dev/null | sed 's/.*: //' || echo "unknown")"
    cores="$(grep -c ^processor /proc/cpuinfo 2>/dev/null || echo "0")"
    # Physical cores via core id
    local phys
    phys="$(grep '^core id' /proc/cpuinfo 2>/dev/null | sort -u | wc -l || echo "0")"
    if [[ "${phys}" -gt 0 ]]; then
      cores="${phys}"
    fi
  fi
  if tool_available nproc; then
    threads="$(nproc 2>/dev/null || echo "0")"
  fi
  printf '{"model": %s, "cores": %s, "threads": %s, "architecture": %s}' \
    "$(json_string "${model}")" \
    "$(json_int "${cores}")" \
    "$(json_int "${threads}")" \
    "$(json_string "${arch}")"
}

collect_memory() {
  local total_mib=0 avail_mib=0
  local total_kb avail_kb
  total_kb="$(grep -oP '(?<=^MemTotal:)\s*[0-9]+' /proc/meminfo 2>/dev/null | tr -d ' ' || true)"
  avail_kb="$(grep -oP '(?<=^MemAvailable:)\s*[0-9]+' /proc/meminfo 2>/dev/null | tr -d ' ' || true)"
  if [[ -n "${total_kb}" ]]; then
    total_mib=$(( total_kb / 1024 ))
  fi
  if [[ -n "${avail_kb}" ]]; then
    avail_mib=$(( avail_kb / 1024 ))
  fi
  printf '{"total_mib": %s, "available_mib": %s}' \
    "$(json_int "${total_mib}")" \
    "$(json_int "${avail_mib}")"
}

collect_dmi() {
  local product_name="" product_uuid="" vendor="" bios_version=""
  product_name="$(read_sysfs_file "/sys/devices/virtual/dmi/id/product_name")"
  product_uuid="$(read_sysfs_file "/sys/devices/virtual/dmi/id/product_uuid")"
  vendor="$(read_sysfs_file "/sys/devices/virtual/dmi/id/sys_vendor")"
  bios_version="$(read_sysfs_file "/sys/devices/virtual/dmi/id/bios_version")"
  printf '{"product_name": %s, "product_uuid": %s, "vendor": %s, "bios_version": %s}' \
    "$(json_string "${product_name}")" \
    "$(json_string "${product_uuid}")" \
    "$(json_string "${vendor}")" \
    "$(json_string "${bios_version}")"
}

detect_hypervisor() {
  if tool_available systemd-detect-virt; then
    systemd-detect-virt 2>/dev/null || echo "none"
  elif [[ -f /sys/devices/virtual/dmi/id/product_name ]]; then
    local product
    product="$(cat /sys/devices/virtual/dmi/id/product_name 2>/dev/null || true)"
    case "${product,,}" in
      *virtualbox*) echo "oracle" ;;
      *vmware*)     echo "vmware" ;;
      *kvm*|*qemu*) echo "kvm" ;;
      *)            echo "none" ;;
    esac
  else
    echo "unknown"
  fi
}

collect_tools() {
  local first=1
  printf '{\n'
  for tool in efibootmgr mokutil lsblk blkid findmnt df ip dmidecode lsusb python3 git; do
    if [[ ${first} -eq 0 ]]; then
      printf ',\n'
    fi
    first=0
    local version
    version="$(check_tool_version "${tool}")"
    printf '    %s: %s' "$(json_string "${tool}")" "$(json_null_or_string "${version}")"
  done
  printf '\n  }'
}

# ---------------------------------------------------------------------------
# Human-readable output
# ---------------------------------------------------------------------------

print_human() {
  local machine_name="$1"
  local kernel="$2"
  local distro_json="$3"
  local cpu_json="$4"
  local memory_json="$5"
  local dmi_json="$6"
  local hypervisor="$7"

  local distro_id distro_ver distro_pretty
  distro_id="$(printf '%s' "${distro_json}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id','unknown'))" 2>/dev/null || echo "unknown")"
  distro_ver="$(printf '%s' "${distro_json}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('version','unknown'))" 2>/dev/null || echo "unknown")"
  local cpu_model
  cpu_model="$(printf '%s' "${cpu_json}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('model','unknown'))" 2>/dev/null || echo "unknown")"
  local cpu_cores cpu_threads
  cpu_cores="$(printf '%s' "${cpu_json}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('cores',0))" 2>/dev/null || echo "0")"
  cpu_threads="$(printf '%s' "${cpu_json}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('threads',0))" 2>/dev/null || echo "0")"
  local mem_total
  mem_total="$(printf '%s' "${memory_json}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total_mib',0))" 2>/dev/null || echo "0")"
  local dmi_product dmi_vendor
  dmi_product="$(printf '%s' "${dmi_json}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('product_name',''))" 2>/dev/null || echo "")"
  dmi_vendor="$(printf '%s' "${dmi_json}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('vendor',''))" 2>/dev/null || echo "")"

  printf '# System Capture — %s\n\n' "${machine_name}"
  printf '## System\n\n'
  printf '| Property | Value |\n'
  printf '|---|---|\n'
  printf '| Machine | %s |\n' "${machine_name}"
  printf '| Distribution | %s %s |\n' "${distro_id}" "${distro_ver}"
  printf '| Kernel | %s |\n' "${kernel}"
  printf '| Hypervisor | %s |\n' "${hypervisor}"
  printf '\n## CPU\n\n'
  printf '| Property | Value |\n'
  printf '|---|---|\n'
  printf '| Model | %s |\n' "${cpu_model}"
  printf '| Cores | %s |\n' "${cpu_cores}"
  printf '| Threads | %s |\n' "${cpu_threads}"
  printf '\n## Memory\n\n'
  printf '| Property | Value |\n'
  printf '|---|---|\n'
  printf '| Total | %s MiB |\n' "${mem_total}"
  printf '\n## DMI\n\n'
  printf '| Property | Value |\n'
  printf '|---|---|\n'
  printf '| Vendor | %s |\n' "${dmi_vendor}"
  printf '| Product | %s |\n' "${dmi_product}"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

main() {
  # Parse arguments
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --dir)
        OUTPUT_DIR="$2"
        shift 2
        ;;
      --human)
        HUMAN_ONLY=true
        shift
        ;;
      *)
        log_error "Unknown option: $1"
        printf 'Usage: %s [--dir <path>] [--human]\n' "$0"
        exit 1
        ;;
    esac
  done

  # Collect data
  local machine_name timestamp kernel distro_json cpu_json memory_json dmi_json hypervisor tools_json
  machine_name="${HOSTNAME:-unknown}"
  timestamp="$(date --iso-8601=seconds 2>/dev/null || date -u +'%Y-%m-%dT%H:%M:%SZ')"
  kernel="$(collect_kernel)"
  distro_json="$(collect_distribution)"
  cpu_json="$(collect_cpu)"
  memory_json="$(collect_memory)"
  dmi_json="$(collect_dmi)"
  hypervisor="$(detect_hypervisor)"

  # Human-readable output
  if [[ "${HUMAN_ONLY}" == true ]]; then
    print_human "${machine_name}" "${kernel}" "${distro_json}" "${cpu_json}" "${memory_json}" "${dmi_json}" "${hypervisor}"
    exit 0
  fi

  # Collect tool versions (only for JSON output)
  tools_json="$(collect_tools)"

  # JSON output
  emit_json_object_start
  emit_json_field "timestamp" "$(json_string "${timestamp}")"
  emit_json_field "machine_name" "$(json_string "${machine_name}")"
  emit_json_field "kernel" "$(json_string "${kernel}")"
  printf '  "distribution": %s,\n' "${distro_json}"
  printf '  "cpu": %s,\n' "${cpu_json}"
  printf '  "memory": %s,\n' "${memory_json}"
  printf '  "dmi": %s,\n' "${dmi_json}"
  emit_json_field "hypervisor" "$(json_string "${hypervisor}")"
  printf '  "tools": %s\n' "${tools_json}"
  emit_json_object_end

  # Write to output directory if specified
  if [[ -n "${OUTPUT_DIR}" ]]; then
    mkdir -p "${OUTPUT_DIR}"
    # Re-run to capture JSON to file
    # (We already have stdout, so write summary as well)
    print_human "${machine_name}" "${kernel}" "${distro_json}" "${cpu_json}" "${memory_json}" "${dmi_json}" "${hypervisor}" \
      > "${OUTPUT_DIR}/system-summary.md" 2>/dev/null || log_warn "Could not write system-summary.md"
    # Write JSON data by re-executing ourselves
    "$0" > "${OUTPUT_DIR}/system.json" 2>/dev/null || log_warn "Could not write system.json"
    log_info "System capture written to ${OUTPUT_DIR}/"
  fi
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
