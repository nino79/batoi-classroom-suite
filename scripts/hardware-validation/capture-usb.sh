#!/usr/bin/env bash
# capture-usb.sh — Capture USB topology, controllers, and attached devices.
#
# Outputs JSON to stdout with keys: timestamp, machine_name, controllers,
# devices, removable_storage.
#
# Usage:
#   ./scripts/hardware-validation/capture-usb.sh
#   ./scripts/hardware-validation/capture-usb.sh --dir /path/to/capture
#   ./scripts/hardware-validation/capture-usb.sh --human
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

collect_usb_tree() {
  # Use lsusb for USB device tree (verbose output includes descriptors).
  if tool_available lsusb; then
    local tree_output
    tree_output="$(lsusb 2>/dev/null || true)"
    local verbose_output
    verbose_output="$(lsusb -v 2>/dev/null || true)"

    if tool_available python3; then
      printf '%s\n===VERBOSE===\n%s' "${tree_output}" "${verbose_output}" | python3 -c "
import sys, re, json

text = sys.stdin.read()
parts = text.split('===VERBOSE===')
tree_text = parts[0] if len(parts) > 0 else ''
verbose_text = parts[1] if len(parts) > 1 else ''

controllers = []
devices = []
removable = []

# Parse lsusb tree
for line in tree_text.strip().split('\n'):
    m = re.match(r'Bus (\d+) Device (\d+): ID ([0-9a-fA-F]{4}):([0-9a-fA-F]{4})\s+(.*)', line)
    if m:
        bus = m.group(1)
        dev = m.group(2)
        vid = m.group(3).lower()
        pid = m.group(4).lower()
        desc = m.group(5).strip()
        entry = {'bus': bus, 'device': dev, 'vendor': vid, 'product': pid, 'description': desc}

        # Hubs and controllers
        if 'hub' in desc.lower() or 'controller' in desc.lower() or 'root' in desc.lower():
            controllers.append(entry)
        else:
            devices.append(entry)

# Try to identify removable storage by looking for 'Mass Storage' or similar
# in verbose output
if verbose_text:
    current_bus = ''
    current_dev = ''
    is_storage = False
    for line in verbose_text.split('\n'):
        dm = re.match(r'Bus (\d+) Device (\d+):', line)
        if dm:
            current_bus = dm.group(1)
            current_dev = dm.group(2)
            is_storage = False
        if 'bInterfaceClass' in line and 'Mass Storage' in line:
            is_storage = True
        if 'iProduct' in line and is_storage:
            # Mark device as removable storage
            for d in devices:
                if d['bus'] == current_bus and d['device'] == current_dev:
                    d['removable_storage'] = True
                    break

for d in devices:
    d.setdefault('removable_storage', False)
    if d['removable_storage']:
        removable.append(d)

result = {
    'controllers': controllers,
    'devices': devices,
    'removable_storage': removable,
}
print(json.dumps(result, indent=2))
" 2>/dev/null || echo '{"controllers": [], "devices": [], "removable_storage": []}'
    else
      echo '{"controllers": [], "devices": [], "removable_storage": []}'
    fi
  else
    # Fallback: parse /sys/bus/usb/devices
    collect_usb_sysfs
  fi
}

collect_usb_sysfs() {
  local first=1
  printf '{"controllers": [\n'
  for dev_dir in /sys/bus/usb/devices/usb*; do
    local name
    name="$(basename "${dev_dir}")"
    [[ "${name}" == "usb"* ]] || continue
    if [[ ${first} -eq 0 ]]; then
      printf ',\n'
    fi
    first=0
    local vendor product manufacturer product_desc speed
    vendor="$(read_sysfs_file "${dev_dir}/idVendor")"
    product="$(read_sysfs_file "${dev_dir}/idProduct")"
    manufacturer="$(read_sysfs_file "${dev_dir}/manufacturer")"
    product_desc="$(read_sysfs_file "${dev_dir}/product")"
    speed="$(read_sysfs_file "${dev_dir}/speed")"
    printf '  {\n'
    printf '    "name": %s,\n' "$(json_string "${name}")"
    printf '    "vendor": %s,\n' "$(json_string "${vendor}")"
    printf '    "product": %s,\n' "$(json_string "${product}")"
    printf '    "manufacturer": %s,\n' "$(json_string "${manufacturer}")"
    printf '    "description": %s,\n' "$(json_string "${product_desc}")"
    printf '    "speed": %s\n' "$(json_string "${speed}")"
    printf '  }'
  done
  printf '\n],\n'

  printf '"devices": [\n'
  first=1
  for dev_dir in /sys/bus/usb/devices/*-*; do
    [[ -d "${dev_dir}" ]] || continue
    if [[ ${first} -eq 0 ]]; then
      printf ',\n'
    fi
    first=0
    local vendor product manufacturer product_desc removable
    vendor="$(read_sysfs_file "${dev_dir}/idVendor")"
    product="$(read_sysfs_file "${dev_dir}/idProduct")"
    manufacturer="$(read_sysfs_file "${dev_dir}/manufacturer")"
    product_desc="$(read_sysfs_file "${dev_dir}/product")"
    # Check for mass storage via bInterfaceClass
    local if_class
    if_class="$(read_sysfs_file "${dev_dir}/bInterfaceClass")"
    removable="false"
    if [[ "${if_class}" == "08" ]]; then
      removable="true"
    fi
    printf '  {\n'
    printf '    "vendor": %s,\n' "$(json_string "${vendor}")"
    printf '    "product": %s,\n' "$(json_string "${product}")"
    printf '    "manufacturer": %s,\n' "$(json_string "${manufacturer}")"
    printf '    "description": %s,\n' "$(json_string "${product_desc}")"
    printf '    "removable_storage": %s\n' "${removable}"
    printf '  }'
  done
  printf '\n],\n'

  printf '"removable_storage": []\n'
  printf '}\n'
}

# ---------------------------------------------------------------------------
# Human-readable output
# ---------------------------------------------------------------------------

print_human() {
  local machine_name="$1"
  local usb_json="$2"

  printf '# USB Capture — %s\n\n' "${machine_name}"

  if tool_available python3; then
    printf '%s' "${usb_json}" | python3 -c "
import sys, json
data = json.load(sys.stdin)
controllers = data.get('controllers', [])
devices = data.get('devices', [])
removable = data.get('removable_storage', [])

print('## USB Controllers\n')
if controllers:
    print('| Bus | Vendor | Product | Description |')
    print('|---|---|---|---|')
    for c in controllers:
        print(f'| {c.get(\"bus\", c.get(\"name\",\"?\"))} | {c.get(\"vendor\",\"\")} | {c.get(\"product\",\"\")} | {c.get(\"description\",\"\")} |')
else:
    print('_No controllers detected._')

print()
print('## USB Devices\n')
if devices:
    print('| Vendor | Product | Description | Removable Storage |')
    print('|---|---|---|---|')
    for d in devices:
        rs = 'yes' if d.get('removable_storage', False) else 'no'
        print(f'| {d.get(\"vendor\",\"\")} | {d.get(\"product\",\"\")} | {d.get(\"description\",\"\")} | {rs} |')
else:
    print('_No devices detected._')

print()
print('## Removable Storage\n')
if removable:
    for d in removable:
        print(f'- {d.get(\"description\",\"Unknown device\")} ({d.get(\"vendor\",\"?\")}:{d.get(\"product\",\"?\")})')
else:
    print('_No removable USB storage detected._')
" 2>/dev/null || printf '%s\n' "${usb_json}"
  else
    printf '%s\n' "${usb_json}"
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

  local machine_name timestamp usb_json
  machine_name="${HOSTNAME:-unknown}"
  timestamp="$(date --iso-8601=seconds 2>/dev/null || date -u +'%Y-%m-%dT%H:%M:%SZ')"
  usb_json="$(collect_usb_tree)"

  if [[ "${HUMAN_ONLY}" == true ]]; then
    print_human "${machine_name}" "${usb_json}"
    exit 0
  fi

  emit_json_object_start
  emit_json_field "timestamp" "$(json_string "${timestamp}")"
  emit_json_field "machine_name" "$(json_string "${machine_name}")"
  printf '  "usb": %s\n' "${usb_json}"
  emit_json_object_end

  if [[ -n "${OUTPUT_DIR}" ]]; then
    mkdir -p "${OUTPUT_DIR}"
    "$0" > "${OUTPUT_DIR}/usb.json" 2>/dev/null || log_warn "Could not write usb.json"
    "$0" --human > "${OUTPUT_DIR}/usb-summary.md" 2>/dev/null || log_warn "Could not write usb-summary.md"
    log_info "USB capture written to ${OUTPUT_DIR}/"
  fi
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
