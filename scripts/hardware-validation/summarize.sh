#!/usr/bin/env bash
# summarize.sh — Generate Beta validation summary report from multiple captures.
#
# Accepts one or more capture directories (produced by capture-all.sh) and
# generates a comprehensive Beta validation report as Markdown.
#
# Usage:
#   ./scripts/hardware-validation/summarize.sh capture1/ capture2/ capture3/
#   ./scripts/hardware-validation/summarize.sh --dir captures/ --output report.md
#   ./scripts/hardware-validation/summarize.sh capture*/  # glob expansion
#
# Output structure:
#   - Number of validated machines
#   - Hardware matrix (CPU, memory, storage, network)
#   - Firmware support (UEFI, Secure Boot)
#   - Supported configurations
#   - Unsupported configurations
#   - Missing tools per machine
#   - Warnings
#
# Exit codes: 0 on success, 1 on error.

set -euo pipefail
IFS=$'\n\t'

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/_shared.sh"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OUTPUT_FILE=""

# ---------------------------------------------------------------------------
# Analysis functions
# ---------------------------------------------------------------------------

read_json_field() {
  local file="$1"
  local field="$2"
  local default="${3:-unknown}"

  if [[ ! -f "${file}" ]]; then
    printf '%s' "${default}"
    return
  fi
  if ! tool_available python3; then
    printf '%s' "${default}"
    return
  fi

  local result
  result="$(python3 -c "
import sys, json
with open('${file}') as f:
    data = json.load(f)
parts = '${field}'.split('.')
val = data
for p in parts:
    if isinstance(val, dict):
        val = val.get(p, {})
    else:
        val = '${default}'
        break
if isinstance(val, (dict, list)):
    val = json.dumps(val)
print(str(val)[:200])
" 2>/dev/null || printf '%s' "${default}")"
  printf '%s' "${result}"
}

collect_machine_summary() {
  local dir="$1"
  local sys_file="${dir}/system.json"

  if [[ ! -f "${sys_file}" ]]; then
    printf '%s|?|?|?|?|?|?|?|?' "$(basename "${dir}")"
    return
  fi

  local machine kernel distro_id distro_ver cpu_model cpu_cores mem_total
  local uefi sb dmi_product vendor hypervisor
  local fw_file="${dir}/firmware.json"

  machine="$(read_json_field "${sys_file}" "machine_name" "$(basename "${dir}")")"
  kernel="$(read_json_field "${sys_file}" "kernel" "?")"
  distro_id="$(read_json_field "${sys_file}" "distribution.id" "?")"
  distro_ver="$(read_json_field "${sys_file}" "distribution.version" "?")"
  cpu_model="$(read_json_field "${sys_file}" "cpu.model" "?")"
  cpu_cores="$(read_json_field "${sys_file}" "cpu.cores" "0")"
  mem_total="$(read_json_field "${sys_file}" "memory.total_mib" "0")"
  hypervisor="$(read_json_field "${sys_file}" "hypervisor" "?")"

  if [[ -f "${fw_file}" ]]; then
    uefi="$(read_json_field "${fw_file}" "uefi" "?")"
    sb="$(read_json_field "${fw_file}" "secure_boot" "?")"
  else
    uefi="?"
    sb="?"
  fi

  dmi_product="$(read_json_field "${sys_file}" "dmi.product_name" "?")"
  vendor="$(read_json_field "${sys_file}" "dmi.vendor" "?")"

  printf '%s|%s|%s %s|%s|%s|%s MiB|%s|%s|%s|%s|%s|%s' \
    "${machine}" "${hypervisor}" "${distro_id}" "${distro_ver}" \
    "${kernel:0:60}" "${cpu_model:0:60}" "${mem_total}" \
    "${uefi}" "${sb}" "${dmi_product:0:60}" "${vendor:0:40}" "${cpu_cores}"
}

analyze_tools() {
  local dir="$1"

  local sys_file="${dir}/system.json"
  if [[ ! -f "${sys_file}" ]]; then
    return
  fi

  if tool_available python3; then
    python3 -c "
import json
with open('${sys_file}') as f:
    data = json.load(f)
tools = data.get('tools', {})
missing = [t for t, v in tools.items() if v == 'null']
present = [t for t, v in tools.items() if v != 'null']
print(f'missing={len(missing)} present={len(present)}')
if missing:
    print('missing_list=' + ','.join(missing))
" 2>/dev/null || true
  fi
}

check_unsupported() {
  local dir="$1"

  local warnings=""

  # Check firmware: must be UEFI
  local fw_file="${dir}/firmware.json"
  if [[ -f "${fw_file}" ]]; then
    local uefi sb
    uefi="$(read_json_field "${fw_file}" "uefi" "")"
    sb="$(read_json_field "${fw_file}" "secure_boot" "")"
    if [[ "${uefi}" != "true" ]]; then
      warnings="${warnings}- ⚠️ **Not UEFI** — BCS requires UEFI firmware\n"
    fi
    if [[ "${sb}" == "enabled" ]]; then
      warnings="${warnings}- ℹ️ Secure Boot is **enabled** — verify BCS compatibility\n"
    fi
  fi

  # Check storage: should have at least one NVMe device
  local storage_file="${dir}/storage.json"
  if [[ -f "${storage_file}" ]]; then
    if tool_available python3; then
      local storage_warnings
      storage_warnings="$(python3 -c "
import json
with open('${storage_file}') as f:
    data = json.load(f)
devices = data.get('devices', [])
if isinstance(devices, dict):
    devices = devices.get('blockdevices', [])
warnings = []
nvme_count = 0
for dev in devices:
    name = dev.get('name', '')
    if 'nvme' in name:
        nvme_count += 1
    # Check for SATA-only (no NVMe)
if nvme_count == 0:
    warnings.append('- ⚠️ **No NVMe storage detected** — BCS is optimized for NVMe')
print('\\n'.join(warnings))
" 2>/dev/null || true)"
      if [[ -n "${storage_warnings}" ]]; then
        warnings="${warnings}${storage_warnings}\n"
      fi
    fi
  fi

  # Check network: should have at least one active interface (not loopback)
  local net_file="${dir}/network.json"
  if [[ -f "${net_file}" ]]; then
    if tool_available python3; then
      local net_warnings
      net_warnings="$(python3 -c "
import json
with open('${net_file}') as f:
    data = json.load(f)
ifaces = data.get('interfaces', [])
warnings = []
active = [i for i in ifaces if i.get('state') == 'up' and i.get('name') != 'lo']
if not active:
    warnings.append('- ⚠️ **No active network interfaces** — deployment requires networking')
print('\\n'.join(warnings))
" 2>/dev/null || true)"
      if [[ -n "${net_warnings}" ]]; then
        warnings="${warnings}${net_warnings}\n"
      fi
    fi
  fi

  printf '%s' "${warnings}"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

main() {
  local -a capture_dirs=()

  # Parse arguments
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --output|-o)
        OUTPUT_FILE="$2"
        shift 2
        ;;
      --dir|-d)
        # Scan directory for capture subdirectories
        if [[ -d "$2" ]]; then
          for subdir in "$2"/*/; do
            if [[ -f "${subdir}/system.json" ]]; then
              capture_dirs+=("${subdir}")
            fi
          done
          if [[ ${#capture_dirs[@]} -eq 0 ]]; then
            log_error "No capture directories found in $2"
            exit 1
          fi
        fi
        shift 2
        ;;
      -*)
        log_error "Unknown option: $1"
        printf 'Usage: %s [--dir <path> | capture-dir...] [--output <file>]\n' "$0"
        exit 1
        ;;
      *)
        capture_dirs+=("$1")
        shift
        ;;
    esac
  done

  # At least one capture directory required
  if [[ ${#capture_dirs[@]} -eq 0 ]]; then
    log_error "No capture directories specified"
    printf 'Usage: %s [--dir <path> | capture-dir...] [--output <file>]\n' "$0"
    exit 1
  fi

  log_info "Processing ${#capture_dirs[@]} capture(s)…"

  # Collect machine summaries
  declare -a machine_summaries
  local all_warnings=""
  local -a tool_analysis

  for dir in "${capture_dirs[@]}"; do
    local summary
    summary="$(collect_machine_summary "${dir}")"
    machine_summaries+=("${summary}")

    local tools
    tools="$(analyze_tools "${dir}")"
    tool_analysis+=("${tools}|$(basename "${dir}")")

    local warnings
    warnings="$(check_unsupported "${dir}")"
    if [[ -n "${warnings}" ]]; then
      all_warnings="${all_warnings}### $(basename "${dir}")\n${warnings}\n"
    fi
  done

  # Count configurations
  local uefi_count=0 non_uefi_count=0
  local nvme_count=0 no_nvme_count=0
  local sb_enabled=0 sb_disabled=0 sb_unknown=0
  local vm_count=0 physical_count=0

  for summary in "${machine_summaries[@]}"; do
    IFS='|' read -r _ hypervisor _ _ _ _ _ uefi sb _ _ _ <<< "${summary}"
    if [[ "${uefi}" == "true" ]]; then
      (( uefi_count++ )) || true
    else
      (( non_uefi_count++ )) || true
    fi
    case "${sb}" in
      enabled)  (( sb_enabled++ )) || true ;;
      disabled) (( sb_disabled++ )) || true ;;
      *)        (( sb_unknown++ )) || true ;;
    esac
    case "${hypervisor}" in
      none) (( physical_count++ )) || true ;;
      *)    (( vm_count++ )) || true ;;
    esac
  done

  # Count storage
  for dir in "${capture_dirs[@]}"; do
    local storage_file="${dir}/storage.json"
    if [[ -f "${storage_file}" && -x /usr/bin/python3 ]]; then
      local has_nvme
      has_nvme="$(python3 -c "
import json
with open('${storage_file}') as f:
    data = json.load(f)
devices = data.get('devices', [])
if isinstance(devices, dict):
    devices = devices.get('blockdevices', [])
for d in devices:
    if 'nvme' in d.get('name', '').lower():
        print('yes')
        exit(0)
print('no')
" 2>/dev/null || echo "unknown")"
      if [[ "${has_nvme}" == "yes" ]]; then
        (( nvme_count++ )) || true
      elif [[ "${has_nvme}" == "no" ]]; then
        (( no_nvme_count++ )) || true
      fi
    fi
  done

  # Generate report
  local report_datetime
  report_datetime="$(date --iso-8601=seconds 2>/dev/null || date -u +'%Y-%m-%dT%H:%M:%SZ')"

  local report
  report="$(
    printf '# Beta Validation Report\n\n'
    printf '**Generated:** %s  \n' "${report_datetime}"
    printf '**Machines validated:** %d  \n\n' "${#capture_dirs[@]}"

    # Executive summary
    printf '## Executive Summary\n\n'
    printf '| Metric | Value |\n'
    printf '|---|---|\n'
    printf '| Total machines | %d |\n' "${#capture_dirs[@]}"
    printf '| Physical machines | %d |\n' "${physical_count}"
    printf '| Virtual machines | %d |\n' "${vm_count}"
    printf '| UEFI firmware | %d |\n' "${uefi_count}"
    printf '| Non-UEFI firmware | %d |\n' "${non_uefi_count}"
    printf '| Secure Boot enabled | %d |\n' "${sb_enabled}"
    printf '| Secure Boot disabled | %d |\n' "${sb_disabled}"
    printf '| Secure Boot unknown | %d |\n' "${sb_unknown}"
    printf '| NVMe storage | %d |\n' "${nvme_count}"
    printf '| No NVMe storage | %d |\n' "${no_nvme_count}"

    # Hardware matrix
    printf '\n## Hardware Matrix\n\n'
    printf '| Machine | Hypervisor | OS | Kernel | CPU | Cores | Memory | UEFI | Secure Boot | Product | Vendor |\n'
    printf '|---|---|---|---|---|---|---|---|---|---|---|\n'
    for summary in "${machine_summaries[@]}"; do
      IFS='|' read -r machine hypervisor os kernel cpu mem uefi sb product vendor cores <<< "${summary}"
      local uefi_icon sb_icon
      if [[ "${uefi}" == "true" ]]; then uefi_icon="✅"; else uefi_icon="❌"; fi
      case "${sb}" in
        enabled)  sb_icon="🔒" ;;
        disabled) sb_icon="✅" ;;
        *)        sb_icon="❓" ;;
      esac
      printf '| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |\n' \
        "${machine}" "${hypervisor}" "${os}" "${kernel}" "${cpu}" "${cores}" "${mem}" "${uefi_icon}" "${sb_icon}" "${product}" "${vendor}"
    done

    # Firmware support summary
    printf '\n## Firmware Support\n\n'
    printf '| Configuration | Count |\n'
    printf '|---|---|\n'
    printf '| UEFI + Secure Boot disabled | %d |\n' "${sb_disabled}"
    printf '| UEFI + Secure Boot enabled | %d |\n' "${sb_enabled}"
    printf '| UEFI + Secure Boot unknown | %d |\n' "${sb_unknown}"
    printf '| Legacy BIOS (non-UEFI) | %d |\n' "${non_uefi_count}"

    # Storage support summary
    printf '\n## Storage Support\n\n'
    printf '| Configuration | Count |\n'
    printf '|---|---|\n'
    printf '| NVMe detected | %d |\n' "${nvme_count}"
    printf '| No NVMe | %d |\n' "${no_nvme_count}"

    # Network support summary
    printf '\n## Network Support\n\n'
    local net_ok=0 net_issue=0
    for dir in "${capture_dirs[@]}"; do
      local net_file="${dir}/network.json"
      if [[ -f "${net_file}" ]]; then
        local has_active
        has_active="$(python3 -c "
import json
with open('${net_file}') as f:
    data = json.load(f)
ifaces = data.get('interfaces', [])
active = [i for i in ifaces if i.get('state') == 'up' and i.get('name') != 'lo']
print(len(active))
" 2>/dev/null || echo "0")"
        if [[ "${has_active}" -gt 0 ]]; then
          (( net_ok++ )) || true
        else
          (( net_issue++ )) || true
        fi
      fi
    done
    printf '| Active network | %d |\n' "${net_ok}"
    printf '| No active network | %d |\n' "${net_issue}"

    # Tool availability
    printf '\n## Tool Availability\n\n'
    for entry in "${tool_analysis[@]}"; do
      local tool_data dir_name
      IFS='|' read -r tool_data dir_name <<< "${entry}"
      local missing present
      missing="$(printf '%s' "${tool_data}" | grep -oP 'missing=\K[0-9]+' || echo "0")"
      present="$(printf '%s' "${tool_data}" | grep -oP 'present=\K[0-9]+' || echo "0")"
      local missing_list
      missing_list="$(printf '%s' "${tool_data}" | grep -oP 'missing_list=\K.*' || true)"
      printf '**%s:** %d present, %d missing  \n' "${dir_name}" "${present}" "${missing}"
      if [[ -n "${missing_list}" ]]; then
        printf '  - Missing: %s  \n' "${missing_list//,/, }"
      fi
    done

    # Unsupported configurations
    printf '\n## Unsupported Configurations\n\n'
    if [[ -n "${all_warnings}" ]]; then
      printf '%s\n' "${all_warnings}"
    else
      printf '_No unsupported configurations detected._\n'
    fi

    # Warnings
    printf '\n## Warnings\n\n'
    local warning_count=0
    # Count non-uefi
    if [[ "${non_uefi_count}" -gt 0 ]]; then
      printf '1. ⚠️ %d machine(s) are not running UEFI firmware — these are **not supported** by BCS\n' "${non_uefi_count}"
      (( warning_count++ )) || true
    fi
    if [[ "${sb_enabled}" -gt 0 ]]; then
      printf '2. ℹ️ %d machine(s) have Secure Boot enabled — verify BCS adapter compatibility\n' "${sb_enabled}"
      (( warning_count++ )) || true
    fi
    if [[ "${no_nvme_count}" -gt 0 ]]; then
      printf '3. ⚠️ %d machine(s) do not have NVMe storage — deployment performance may be affected\n' "${no_nvme_count}"
      (( warning_count++ )) || true
    fi
    if [[ "${net_issue}" -gt 0 ]]; then
      printf '4. ⚠️ %d machine(s) have no active network interfaces\n' "${net_issue}"
      (( warning_count++ )) || true
    fi
    if [[ "${warning_count}" -eq 0 ]]; then
      printf '_No warnings._\n'
    fi

    # Recommendations
    printf '\n## Recommendations\n\n'
    if [[ "${non_uefi_count}" -gt 0 ]]; then
      printf '- **UEFI firmware required:** Machines without UEFI cannot run BCS. Switch to UEFI mode in firmware settings.\n'
    fi
    if [[ "${sb_enabled}" -gt 0 ]]; then
      printf '- **Secure Boot testing:** Run the Secure Boot adapter tests on machines with Secure Boot enabled to validate compatibility.\n'
    fi
    if [[ "${no_nvme_count}" -gt 0 ]]; then
      printf '- **NVMe storage recommended:** BCS is optimized for NVMe. SATA/SCSI storage will work but may have reduced performance.\n'
    fi
    if [[ "${warning_count}" -eq 0 ]]; then
      printf '_All configurations are within expected parameters._\n'
    fi
  )"

  # Write output
  if [[ -n "${OUTPUT_FILE}" ]]; then
    printf '%s\n' "${report}" > "${OUTPUT_FILE}"
    log_info "Report written to ${OUTPUT_FILE}"
  else
    printf '%s\n' "${report}"
  fi

  log_info "Summary complete — ${#capture_dirs[@]} machine(s) analyzed"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
