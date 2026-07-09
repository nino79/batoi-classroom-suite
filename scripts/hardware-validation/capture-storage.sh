#!/usr/bin/env bash
# capture-storage.sh — Capture block device, partition, and filesystem topology.
#
# Outputs JSON to stdout with keys: timestamp, machine_name, devices, filesystems.
# Each device entry includes partitions with mountpoints, UUIDs, and filesystem types.
#
# Usage:
#   ./scripts/hardware-validation/capture-storage.sh
#   ./scripts/hardware-validation/capture-storage.sh --dir /path/to/capture
#   ./scripts/hardware-validation/capture-storage.sh --human
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

collect_devices() {
  # Use lsblk for tree-structured device data (JSON output mode).
  if tool_available lsblk; then
    lsblk --bytes --json --output NAME,KNAME,MODEL,SIZE,TYPE,ROTA,RM,MOUNTPOINT,FSTYPE,UUID,PARTTYPENAME,PKNAME,LABEL 2>/dev/null || true
  else
    printf '[]'
  fi
}

collect_filesystem_usage() {
  # Use df to report filesystem usage.
  if tool_available df; then
    df --output=source,fstype,size,used,avail,pcent,target -x tmpfs -x devtmpfs -x squashfs 2>/dev/null || true
  fi
}

# ---------------------------------------------------------------------------
# Human-readable output
# ---------------------------------------------------------------------------

print_human() {
  local machine_name="$1"
  local devices_json="$2"

  printf '# Storage Capture — %s\n\n' "${machine_name}"

  # Parse devices from lsblk JSON using python3 (preferred) or jq
  if tool_available python3; then
    printf '%s' "${devices_json}" | python3 -c "
import sys, json
data = json.load(sys.stdin)
blockdevices = data.get('blockdevices', [])
print('## Block Devices\n')
print('| Name | Model | Size | Type | ROTA | Removable | Filesystem | Mount | UUID |')
print('|---|---|---|---|---|---|---|---|---|')
def print_device(dev, prefix=''):
    name = prefix + dev.get('name', '?')
    model = dev.get('model', '') or ''
    size = dev.get('size', 0)
    dtype = dev.get('type', '?')
    rota = dev.get('rota', False)
    rm = dev.get('rm', False)
    fstype = dev.get('fstype', '') or ''
    mount = dev.get('mountpoint', '') or ''
    uuid = dev.get('uuid', '') or ''
    size_str = str(size)
    if size >= 1073741824:
        size_str = f'{size / 1073741824:.1f}G'
    elif size >= 1048576:
        size_str = f'{size / 1048576:.1f}M'
    print(f'| {name} | {model} | {size_str} | {dtype} | {\"yes\" if rota else \"no\"} | {\"yes\" if rm else \"no\"} | {fstype} | {mount} | {uuid} |')
    for child in dev.get('children', []):
        print_device(child, prefix + '  ')
for dev in blockdevices:
    print_device(dev)
" 2>/dev/null || printf '_Could not parse device data_\n'
  else
    printf '%s\n' "${devices_json}"
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

  local machine_name timestamp devices_json fs_usage
  machine_name="${HOSTNAME:-unknown}"
  timestamp="$(date --iso-8601=seconds 2>/dev/null || date -u +'%Y-%m-%dT%H:%M:%SZ')"
  devices_json="$(collect_devices)"

  if [[ "${HUMAN_ONLY}" == true ]]; then
    print_human "${machine_name}" "${devices_json}"
    exit 0
  fi

  # Emit JSON
  emit_json_object_start
  emit_json_field "timestamp" "$(json_string "${timestamp}")"
  emit_json_field "machine_name" "$(json_string "${machine_name}")"
  printf '  "devices": %s\n' "${devices_json}"
  emit_json_object_end

  if [[ -n "${OUTPUT_DIR}" ]]; then
    mkdir -p "${OUTPUT_DIR}"
    "$0" > "${OUTPUT_DIR}/storage.json" 2>/dev/null || log_warn "Could not write storage.json"
    "$0" --human > "${OUTPUT_DIR}/storage-summary.md" 2>/dev/null || log_warn "Could not write storage-summary.md"
    log_info "Storage capture written to ${OUTPUT_DIR}/"
  fi
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
