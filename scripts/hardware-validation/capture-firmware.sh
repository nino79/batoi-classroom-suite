#!/usr/bin/env bash
# capture-firmware.sh — Capture UEFI firmware, Secure Boot, and DMI data.
#
# Outputs JSON to stdout with keys: timestamp, machine_name, uefi, secure_boot,
# boot_entries, boot_order, dmi.
#
# Usage:
#   ./scripts/hardware-validation/capture-firmware.sh
#   ./scripts/hardware-validation/capture-firmware.sh --dir /path/to/capture
#   ./scripts/hardware-validation/capture-firmware.sh --human
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

detect_uefi() {
  if [[ -d /sys/firmware/efi ]]; then
    printf 'true'
  else
    printf 'false'
  fi
}

read_secure_boot() {
  local sb_state="unknown"
  if tool_available mokutil; then
    local output
    output="$(mokutil --sb-state 2>/dev/null || true)"
    case "${output,,}" in
      *enabled*)  sb_state="enabled" ;;
      *disabled*) sb_state="disabled" ;;
      *)          sb_state="unknown" ;;
    esac
  elif [[ -f /sys/firmware/efi/efivars/SecureBoot-* ]]; then
    # Fallback: read efivar directly
    local sb_file
    sb_file="$(ls /sys/firmware/efi/efivars/SecureBoot-* 2>/dev/null || true)"
    if [[ -n "${sb_file}" ]]; then
      local val
      val="$(od -An -t u1 "${sb_file}" 2>/dev/null | tr -d ' ' || echo "0")"
      if [[ "${val}" == "1" ]]; then
        sb_state="enabled"
      else
        sb_state="disabled"
      fi
    fi
  fi
  json_string "${sb_state}"
}

read_boot_entries() {
  if ! tool_available efibootmgr; then
    printf '[]'
    return
  fi
  local output
  output="$(efibootmgr 2>/dev/null || true)"
  if [[ -z "${output}" ]]; then
    printf '[]'
    return
  fi
  # Parse efibootmgr output
  if tool_available python3; then
    printf '%s' "${output}" | python3 -c "
import sys, re, json
text = sys.stdin.read()
entries = []
for line in text.splitlines():
    m = re.match(r'Boot([0-9a-fA-F]{4})\*?\s+(.+)', line)
    if m:
        num = m.group(1).lower()
        label = m.group(2).strip()
        active = '*' in line
        entries.append({'number': num, 'label': label, 'active': active})
print(json.dumps(entries, indent=2))
" 2>/dev/null || printf '[]'
  else
    printf '[]'
  fi
}

read_boot_order() {
  if ! tool_available efibootmgr; then
    printf '[]'
    return
  fi
  local output
  output="$(efibootmgr 2>/dev/null || true)"
  if [[ -z "${output}" ]]; then
    printf '[]'
    return
  fi
  local order_line
  order_line="$(printf '%s' "${output}" | grep '^BootOrder:' 2>/dev/null || true)"
  if [[ -n "${order_line}" ]]; then
    local order="${order_line#BootOrder: }"
    order="${order// /}"
    # Format as JSON array of strings
    if tool_available python3; then
      printf '%s' "${order}" | python3 -c "
import sys, json
order = sys.stdin.read().strip().split(',')
print(json.dumps([x.lower() for x in order], indent=2))
" 2>/dev/null || printf '[]'
    else
      printf '[]'
    fi
  else
    printf '[]'
  fi
}

collect_dmi_firmware() {
  # Read DMI data from sysfs (no root required, but less complete than dmidecode).
  local bios_vendor="" bios_version="" bios_date=""
  local sys_man="" sys_product="" sys_version="" sys_serial=""
  local baseboard_man="" baseboard_product=""

  bios_vendor="$(read_sysfs_file "/sys/devices/virtual/dmi/id/bios_vendor")"
  bios_version="$(read_sysfs_file "/sys/devices/virtual/dmi/id/bios_version")"
  bios_date="$(read_sysfs_file "/sys/devices/virtual/dmi/id/bios_date")"
  sys_man="$(read_sysfs_file "/sys/devices/virtual/dmi/id/sys_vendor")"
  sys_product="$(read_sysfs_file "/sys/devices/virtual/dmi/id/product_name")"
  sys_version="$(read_sysfs_file "/sys/devices/virtual/dmi/id/product_version")"
  sys_serial="$(read_sysfs_file "/sys/devices/virtual/dmi/id/product_serial")"

  # Try dmidecode as a richer source (usually needs root; fall back gracefully).
  if tool_available dmidecode; then
    local decoded
    decoded="$(dmidecode -t 0 -t 1 -t 2 2>/dev/null || true)"
    if [[ -n "${decoded}" && "${decoded}" != *"Permission denied"* ]]; then
      if tool_available python3; then
        # Extract BIOS version, system manufacturer, product from dmidecode
        local dmidecode_json
        dmidecode_json="$(printf '%s' "${decoded}" | python3 -c "
import sys, json
text = sys.stdin.read()
result = {}
for section in text.split('Handle '):
    if not section.strip():
        continue
    lines = section.split('\n')
    for line in lines:
        line = line.strip()
        if ':' not in line:
            continue
        key, val = line.split(':', 1)
        key = key.strip()
        val = val.strip()
        if key == 'Vendor':
            result['bios_vendor'] = val
        elif key == 'Version':
            result['bios_version'] = val
        elif key == 'Release Date':
            result['bios_date'] = val
        elif key == 'Manufacturer':
            result['system_manufacturer'] = val
        elif key == 'Product Name':
            result['system_product'] = val
        elif key == 'Version':
            if 'system_version' not in result:
                result['system_version'] = val
        elif key == 'Serial Number':
            result['system_serial'] = val
print(json.dumps(result, indent=2))
" 2>/dev/null || true)"
        if [[ -n "${dmidecode_json}" && "${dmidecode_json}" != "{}" ]]; then
          # Merge — dmidecode values override sysfs when available
          bios_vendor="$(printf '%s' "${dmidecode_json}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('bios_vendor','${bios_vendor}'))" 2>/dev/null || echo "${bios_vendor}")"
          bios_version="$(printf '%s' "${dmidecode_json}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('bios_version','${bios_version}'))" 2>/dev/null || echo "${bios_version}")"
          bios_date="$(printf '%s' "${dmidecode_json}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('bios_date','${bios_date}'))" 2>/dev/null || echo "${bios_date}")"
          sys_man="$(printf '%s' "${dmidecode_json}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('system_manufacturer','${sys_man}'))" 2>/dev/null || echo "${sys_man}")"
          sys_product="$(printf '%s' "${dmidecode_json}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('system_product','${sys_product}'))" 2>/dev/null || echo "${sys_product}")"
          sys_version="$(printf '%s' "${dmidecode_json}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('system_version','${sys_version}'))" 2>/dev/null || echo "${sys_version}")"
          sys_serial="$(printf '%s' "${dmidecode_json}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('system_serial','${sys_serial}'))" 2>/dev/null || echo "${sys_serial}")"
        fi
      fi
    fi
  fi

  printf '{\n'
  printf '    "bios_vendor": %s,\n' "$(json_string "${bios_vendor}")"
  printf '    "bios_version": %s,\n' "$(json_string "${bios_version}")"
  printf '    "bios_date": %s,\n' "$(json_string "${bios_date}")"
  printf '    "system_manufacturer": %s,\n' "$(json_string "${sys_man}")"
  printf '    "system_product_name": %s,\n' "$(json_string "${sys_product}")"
  printf '    "system_version": %s,\n' "$(json_string "${sys_version}")"
  printf '    "system_serial": %s\n' "$(json_string "${sys_serial}")"
  printf '  }'
}

# ---------------------------------------------------------------------------
# Human-readable output
# ---------------------------------------------------------------------------

print_human() {
  local machine_name="$1"
  local uefi="$2"
  local secure_boot="$3"
  local boot_entries_json="$4"
  local boot_order_json="$5"
  local dmi_json="$6"

  printf '# Firmware Capture — %s\n\n' "${machine_name}"
  printf '## Firmware Mode\n\n'
  printf '| Property | Value |\n'
  printf '|---|---|\n'
  printf '| UEFI | %s |\n' "${uefi}"
  printf '| Secure Boot | %s |\n' "${secure_boot}"
  printf '\n## DMI\n\n'
  if tool_available python3; then
    printf '%s' "${dmi_json}" | python3 -c "
import sys, json
dmi = json.load(sys.stdin)
print('| Property | Value |')
print('|---|---|')
for k, v in dmi.items():
    if v:
        print(f'| {k} | {v} |')
" 2>/dev/null
  fi
  printf '\n## Boot Entries\n\n'
  if tool_available python3; then
    printf '%s' "${boot_entries_json}" | python3 -c "
import sys, json
entries = json.load(sys.stdin)
if entries:
    print('| Number | Label | Active |')
    print('|---|---|---|')
    for e in entries:
        print(f'| {e[\"number\"]} | {e[\"label\"]} | {\"yes\" if e[\"active\"] else \"no\"} |')
else:
    print('_No boot entries detected (efibootmgr unavailable or no output)._')
" 2>/dev/null
  fi
  printf '\n## Boot Order\n\n'
  if tool_available python3; then
    local boot_order_str
    boot_order_str="$(printf '%s' "${boot_order_json}" | python3 -c "import sys, json; print(', '.join(json.load(sys.stdin)))" 2>/dev/null || echo "none")"
    printf '%s\n' "${boot_order_str}"
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

  local machine_name timestamp uefi secure_boot boot_entries_json boot_order_json dmi_json
  machine_name="${HOSTNAME:-unknown}"
  timestamp="$(date --iso-8601=seconds 2>/dev/null || date -u +'%Y-%m-%dT%H:%M:%SZ')"
  uefi="$(detect_uefi)"
  secure_boot="$(read_secure_boot)"
  boot_entries_json="$(read_boot_entries)"
  boot_order_json="$(read_boot_order)"
  dmi_json="$(collect_dmi_firmware)"

  if [[ "${HUMAN_ONLY}" == true ]]; then
    print_human "${machine_name}" "${uefi}" "${secure_boot}" "${boot_entries_json}" "${boot_order_json}" "${dmi_json}"
    exit 0
  fi

  emit_json_object_start
  emit_json_field "timestamp" "$(json_string "${timestamp}")"
  emit_json_field "machine_name" "$(json_string "${machine_name}")"
  emit_json_field "uefi" "${uefi}"
  emit_json_field "secure_boot" "${secure_boot}"
  printf '  "boot_entries": %s,\n' "${boot_entries_json}"
  printf '  "boot_order": %s,\n' "${boot_order_json}"
  printf '  "dmi": %s\n' "${dmi_json}"
  emit_json_object_end

  if [[ -n "${OUTPUT_DIR}" ]]; then
    mkdir -p "${OUTPUT_DIR}"
    "$0" > "${OUTPUT_DIR}/firmware.json" 2>/dev/null || log_warn "Could not write firmware.json"
    "$0" --human > "${OUTPUT_DIR}/firmware-summary.md" 2>/dev/null || log_warn "Could not write firmware-summary.md"
    log_info "Firmware capture written to ${OUTPUT_DIR}/"
  fi
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
