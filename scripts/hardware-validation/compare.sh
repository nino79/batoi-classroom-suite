#!/usr/bin/env bash
# compare.sh — Compare two hardware validation captures and generate a diff report.
#
# Accepts two directories (left/right) produced by capture-all.sh and
# writes comparison.md highlighting firmware, storage, network, Secure Boot,
# tooling, and other differences.
#
# Usage:
#   ./scripts/hardware-validation/compare.sh left-dir/ right-dir/
#   ./scripts/hardware-validation/compare.sh left-dir/ right-dir/ --output report.md
#   ./scripts/hardware-validation/compare.sh left-dir/ right-dir/ --verbose
#
# Exit codes: 0 — comparison generated (differences found or not).
#             1 — missing directory or required files.
#             2 — no differences found (not an error, but distinct exit).

set -euo pipefail
IFS=$'\n\t'

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/_shared.sh"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

LEFT_DIR=""
RIGHT_DIR=""
OUTPUT_FILE=""
VERBOSE=false

declare -a REQUIRED_FILES=(
  "system.json"
  "storage.json"
  "network.json"
  "firmware.json"
  "usb.json"
)

# ---------------------------------------------------------------------------
# Comparison functions
# ---------------------------------------------------------------------------

compare_json_field() {
  local left_file="$1"
  local right_file="$2"
  local field="$3"
  local label="${4:-$field}"

  if [[ ! -f "${left_file}" || ! -f "${right_file}" ]]; then
    return
  fi

  if ! tool_available python3; then
    log_warn "python3 required for JSON comparison; skipping ${label}"
    printf '  - **%s:** python3 not available — cannot compare\n' "${label}"
    return
  fi

  local diff_result
  diff_result="$(python3 -c "
import sys, json

with open('${left_file}') as f:
    left = json.load(f)
with open('${right_file}') as f:
    right = json.load(f)

def get_field(obj, path):
    parts = path.split('.')
    for p in parts:
        if isinstance(obj, dict):
            obj = obj.get(p, {})
        else:
            return None
    return obj

left_val = get_field(left, '${field}')
right_val = get_field(right, '${field}')

if left_val != right_val:
    print(f'**{label}:** CHANGED')
    print(f'  - Left:  {json.dumps(left_val)[:200]}')
    print(f'  - Right: {json.dumps(right_val)[:200]}')
else:
    print(f'**{label}:** unchanged')
" 2>/dev/null || true)"

  printf '%s\n' "${diff_result}"
}

compare_json_object() {
  local left_file="$1"
  local right_file="$2"
  local label="$3"

  if [[ ! -f "${left_file}" || ! -f "${right_file}" ]]; then
    printf '  - **%s:** missing file on one side\n' "${label}"
    return
  fi

  if ! tool_available python3; then
    log_warn "python3 required for JSON comparison; skipping ${label}"
    printf '  - **%s:** python3 not available — cannot compare\n' "${label}"
    return
  fi

  python3 -c "
import sys, json

with open('${left_file}') as f:
    left = json.load(f)
with open('${right_file}') as f:
    right = json.load(f)

def deep_diff(l, r, path=''):
    diffs = []
    if type(l) != type(r):
        diffs.append((path, f'type mismatch: {type(l).__name__} vs {type(r).__name__}'))
        return diffs
    if isinstance(l, dict):
        all_keys = set(list(l.keys()) + list(r.keys()))
        for k in sorted(all_keys):
            new_path = f'{path}.{k}' if path else k
            if k not in l:
                diffs.append((new_path, f'added in right: {json.dumps(r[k])[:100]}'))
            elif k not in r:
                diffs.append((new_path, f'removed from right: {json.dumps(l[k])[:100]}'))
            else:
                diffs.extend(deep_diff(l[k], r[k], new_path))
    elif isinstance(l, list):
        if len(l) != len(r):
            diffs.append((path, f'array length: {len(l)} vs {len(r)}'))
        else:
            for i, (lv, rv) in enumerate(zip(l, r)):
                diffs.extend(deep_diff(lv, rv, f'{path}[{i}]'))
    else:
        if l != r:
            diffs.append((path, f'{json.dumps(l)[:100]} vs {json.dumps(r)[:100]}'))
    return diffs

diffs = deep_diff(left, right)
if diffs:
    print(f'**${label}:** {len(diffs)} difference(s)')
    for path, msg in diffs[:20]:
        print(f'  - {path}: {msg}')
    if len(diffs) > 20:
        print(f'  - ... and {len(diffs) - 20} more difference(s)')
else:
    print(f'**${label}:** unchanged')
" 2>/dev/null || printf '  - **%s:** comparison error\n' "${label}"
}

compare_machine_names() {
  local left_file="$1"
  local right_file="$2"

  if [[ ! -f "${left_file}" || ! -f "${right_file}" ]]; then
    return
  fi

  if tool_available python3; then
    python3 -c "
import json
with open('${left_file}') as f: left = json.load(f)
with open('${right_file}') as f: right = json.load(f)
lm = left.get('machine_name', 'unknown')
rm = right.get('machine_name', 'unknown')
if lm != rm:
    print(f'- **Machine:** {lm} (left) vs {rm} (right)')
else:
    print(f'- **Machine:** {lm} (same)')
" 2>/dev/null || true
  fi
}

compare_timestamps() {
  local left_file="$1"
  local right_file="$2"

  if [[ ! -f "${left_file}" || ! -f "${right_file}" ]]; then
    return
  fi

  if tool_available python3; then
    python3 -c "
import json
with open('${left_file}') as f: left = json.load(f)
with open('${right_file}') as f: right = json.load(f)
lt = left.get('timestamp', 'unknown')
rt = right.get('timestamp', 'unknown')
print(f'- **Capture date:** {lt} (left) vs {rt} (right)')
" 2>/dev/null || true
  fi
}

compare_tools() {
  local left_file="$1"
  local right_file="$2"

  if [[ ! -f "${left_file}" || ! -f "${right_file}" ]]; then
    return
  fi

  if tool_available python3; then
    python3 -c "
import json
with open('${left_file}') as f: left = json.load(f)
with open('${right_file}') as f: right = json.load(f)

left_tools = left.get('tools', {})
right_tools = right.get('tools', {})

all_tools = set(list(left_tools.keys()) + list(right_tools.keys()))
for tool in sorted(all_tools):
    lv = left_tools.get(tool, 'null')
    rv = right_tools.get(tool, 'null')
    if lv == 'null' and rv != 'null':
        print(f'- **{tool}:** missing in left, present in right ({rv})')
    elif lv != 'null' and rv == 'null':
        print(f'- **{tool}:** present in left ({lv}), missing in right')
    elif lv != rv:
        print(f'- **{tool}:** {lv} (left) vs {rv} (right)')
    else:
        print(f'- **{tool}:** {lv} (same)')
" 2>/dev/null || true
  fi
}

count_missing_tools() {
  local file="$1"
  if [[ ! -f "${file}" ]]; then
    return
  fi
  if tool_available python3; then
    python3 -c "
import json
with open('${file}') as f: data = json.load(f)
tools = data.get('tools', {})
missing = [t for t, v in tools.items() if v == 'null']
print(len(missing))
" 2>/dev/null || echo "0"
  fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

main() {
  # Parse positional arguments
  if [[ $# -lt 2 ]]; then
    printf 'Usage: %s <left-dir> <right-dir> [--output <file>] [--verbose]\n' "$0"
    exit 1
  fi

  LEFT_DIR="$1"
  RIGHT_DIR="$2"
  shift 2

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --output)
        OUTPUT_FILE="$2"
        shift 2
        ;;
      --verbose)
        VERBOSE=true
        shift
        ;;
      *)
        log_error "Unknown option: $1"
        exit 1
        ;;
    esac
  done

  # Validate directories
  if [[ ! -d "${LEFT_DIR}" ]]; then
    log_error "Left directory not found: ${LEFT_DIR}"
    exit 1
  fi
  if [[ ! -d "${RIGHT_DIR}" ]]; then
    log_error "Right directory not found: ${RIGHT_DIR}"
    exit 1
  fi

  # Determine left/right machine info
  local left_sys="${LEFT_DIR}/system.json"
  local right_sys="${RIGHT_DIR}/system.json"
  local left_machine="left" right_machine="right"

  if [[ -f "${left_sys}" ]]; then
    left_machine="$(python3 -c "import json; print(json.load(open('${left_sys}')).get('machine_name','left'))" 2>/dev/null || echo "left")"
  fi
  if [[ -f "${right_sys}" ]]; then
    right_machine="$(python3 -c "import json; print(json.load(open('${right_sys}')).get('machine_name','right'))" 2>/dev/null || echo "right")"
  fi

  # Start building comparison report
  local report
  report="$(
    printf '# Hardware Validation Comparison\n\n'
    printf '**Compared:** %s (left) vs %s (right)  \n' "${left_machine}" "${right_machine}"
    printf '**Generated:** %s  \n\n' "$(date --iso-8601=seconds 2>/dev/null || date -u +'%Y-%m-%dT%H:%M:%SZ')"

    # --- Summary ---
    printf '## Summary\n\n'
    printf '| Aspect | Status |\n'
    printf '|---|---|\n'

    # Check each required file
    local all_present=true
    for req_file in "${REQUIRED_FILES[@]}"; do
      local left_path="${LEFT_DIR}/${req_file}"
      local right_path="${RIGHT_DIR}/${req_file}"
      if [[ ! -f "${left_path}" ]]; then
        printf '| %s (left) | ❌ Missing |\n' "${req_file}"
        all_present=false
      fi
      if [[ ! -f "${right_path}" ]]; then
        printf '| %s (right) | ❌ Missing |\n' "${req_file}"
        all_present=false
      fi
    done

    if [[ "${all_present}" == false ]]; then
      printf '\n> ⚠️  Some capture files are missing. Comparison will be partial.\n\n'
    fi

    # Machine identity
    compare_machine_names "${left_sys}" "${right_sys}"
    compare_timestamps "${left_sys}" "${right_sys}"

    # --- Firmware comparison ---
    printf '\n## Firmware\n\n'
    local left_fw="${LEFT_DIR}/firmware.json"
    local right_fw="${RIGHT_DIR}/firmware.json"
    if [[ -f "${left_fw}" && -f "${right_fw}" ]]; then
      compare_json_field "${left_fw}" "${right_fw}" "uefi" "UEFI mode"
      compare_json_field "${left_fw}" "${right_fw}" "secure_boot" "Secure Boot"
      compare_json_object "${left_fw}" "${right_fw}" "Boot entries"
    else
      printf '_Firmware data missing on one side._\n'
    fi

    # --- Storage comparison ---
    printf '\n## Storage\n\n'
    local left_stor="${LEFT_DIR}/storage.json"
    local right_stor="${RIGHT_DIR}/storage.json"
    if [[ -f "${left_stor}" && -f "${right_stor}" ]]; then
      compare_json_object "${left_stor}" "${right_stor}" "Devices"
    else
      printf '_Storage data missing on one side._\n'
    fi

    # --- Network comparison ---
    printf '\n## Network\n\n'
    local left_net="${LEFT_DIR}/network.json"
    local right_net="${RIGHT_DIR}/network.json"
    if [[ -f "${left_net}" && -f "${right_net}" ]]; then
      compare_json_object "${left_net}" "${right_net}" "Interfaces"
    else
      printf '_Network data missing on one side._\n'
    fi

    # --- USB comparison ---
    printf '\n## USB\n\n'
    local left_usb="${LEFT_DIR}/usb.json"
    local right_usb="${RIGHT_DIR}/usb.json"
    if [[ -f "${left_usb}" && -f "${right_usb}" ]]; then
      compare_json_object "${left_usb}" "${right_usb}" "USB devices"
    else
      printf '_USB data missing on one side._\n'
    fi

    # --- System comparison ---
    printf '\n## System\n\n'
    if [[ -f "${left_sys}" && -f "${right_sys}" ]]; then
      compare_json_field "${left_sys}" "${right_sys}" "kernel" "Kernel"
      compare_json_field "${left_sys}" "${right_sys}" "hypervisor" "Hypervisor"
      compare_json_field "${left_sys}" "${right_sys}" "cpu.model" "CPU model"
      compare_json_field "${left_sys}" "${right_sys}" "cpu.cores" "CPU cores"
      compare_json_field "${left_sys}" "${right_sys}" "memory.total_mib" "Memory (MiB)"
      compare_json_field "${left_sys}" "${right_sys}" "dmi.product_name" "DMI product"
      compare_json_field "${left_sys}" "${right_sys}" "dmi.vendor" "DMI vendor"
    else
      printf '_System data missing on one side._\n'
    fi

    # --- Distribution comparison ---
    printf '\n## Distribution\n\n'
    if [[ -f "${left_sys}" && -f "${right_sys}" ]]; then
      compare_json_field "${left_sys}" "${right_sys}" "distribution.id" "Distro ID"
      compare_json_field "${left_sys}" "${right_sys}" "distribution.version" "Distro version"
      compare_json_field "${left_sys}" "${right_sys}" "distribution.pretty_name" "Distro name"
    fi

    # --- Tools comparison ---
    printf '\n## Tools\n\n'
    if [[ -f "${left_sys}" && -f "${right_sys}" ]]; then
      compare_tools "${left_sys}" "${right_sys}"
    fi

    # --- Warnings ---
    printf '\n## Warnings\n\n'
    local left_missing="0" right_missing="0"
    if [[ -f "${left_sys}" ]]; then
      left_missing="$(count_missing_tools "${left_sys}")"
    fi
    if [[ -f "${right_sys}" ]]; then
      right_missing="$(count_missing_tools "${right_sys}")"
    fi
    if [[ "${left_missing}" -gt 0 ]]; then
      printf '- ⚠️  Left machine has %s missing tools\n' "${left_missing}"
    fi
    if [[ "${right_missing}" -gt 0 ]]; then
      printf '- ⚠️  Right machine has %s missing tools\n' "${right_missing}"
    fi
    if [[ "${left_missing}" -eq 0 && "${right_missing}" -eq 0 ]]; then
      printf '_No warnings._\n'
    fi
  )"

  # Write output
  if [[ -n "${OUTPUT_FILE}" ]]; then
    printf '%s\n' "${report}" > "${OUTPUT_FILE}"
    log_info "Comparison written to ${OUTPUT_FILE}"
  else
    printf '%s\n' "${report}"
  fi

  # Check if there were any actual differences
  local has_diffs
  has_diffs="$(printf '%s\n' "${report}" | grep -c "CHANGED\|difference\|Missing\|missing\|⚠️" || true)"

  if [[ "${has_diffs}" -eq 0 ]]; then
    log_info "No differences found between captures"
    exit 2
  fi
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
