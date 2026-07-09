#!/usr/bin/env bash
# capture-network.sh — Capture network interface topology and addressing.
#
# Outputs JSON to stdout with keys: timestamp, machine_name, interfaces.
# Each interface entry includes name, MAC, state, IPv4/IPv6 addresses, speed, and duplex.
#
# Usage:
#   ./scripts/hardware-validation/capture-network.sh
#   ./scripts/hardware-validation/capture-network.sh --dir /path/to/capture
#   ./scripts/hardware-validation/capture-network.sh --human
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

collect_interfaces_json() {
  # Use ip -json addr for structured interface data (modern iproute2).
  if tool_available ip; then
    local addr_data link_data
    addr_data="$(ip -json addr show 2>/dev/null || true)"
    link_data="$(ip -json link show 2>/dev/null || true)"
    if [[ -n "${addr_data}" && -n "${link_data}" ]]; then
      # Merge addr and link data using python3
      if tool_available python3; then
        printf '%s\n%s' "${addr_data}" "${link_data}" | python3 -c "
import sys, json
addr_list = json.loads(sys.stdin.readline())
link_list = json.loads(sys.stdin.readline())
link_map = {l.get('ifname'): l for l in link_list}
result = []
for iface in addr_list:
    name = iface.get('ifname', '')
    link = link_map.get(name, {})
    addrs = iface.get('addr_info', [])
    ipv4 = [a['local'] + '/' + str(a['prefixlen']) for a in addrs if a.get('family') == 'inet']
    ipv6 = [a['local'] + '/' + str(a['prefixlen']) for a in addrs if a.get('family') == 'inet6']
    result.append({
        'name': name,
        'mac': link.get('address', iface.get('address', '')),
        'state': link.get('operstate', iface.get('operstate', 'unknown')),
        'mtu': link.get('mtu', iface.get('mtu', 0)),
        'speed': link.get('speed', None),
        'ipv4': ipv4,
        'ipv6': ipv6,
    })
print(json.dumps(result, indent=2))
" 2>/dev/null || echo "[]"
      else
        echo "${addr_data}"
      fi
    else
      echo "[]"
    fi
  else
    # Fallback: parse /sys/class/net
    collect_interfaces_sysfs
  fi
}

collect_interfaces_sysfs() {
  local first=1
  printf '[\n'
  for iface_dir in /sys/class/net/*; do
    local name
    name="$(basename "${iface_dir}")"
    [[ "${name}" == "lo" ]] && continue
    if [[ ${first} -eq 0 ]]; then
      printf ',\n'
    fi
    first=0
    local mac="" state="" mtu=0 speed=""
    mac="$(read_sysfs_file "${iface_dir}/address")"
    state="$(read_sysfs_file "${iface_dir}/operstate")"
    mtu="$(read_sysfs_file "${iface_dir}/mtu")"
    speed="$(read_sysfs_file "${iface_dir}/speed")"
    printf '  {\n'
    printf '    "name": %s,\n' "$(json_string "${name}")"
    printf '    "mac": %s,\n' "$(json_string "${mac}")"
    printf '    "state": %s,\n' "$(json_string "${state}")"
    printf '    "mtu": %s,\n' "$(json_int "${mtu:-0}")"
    printf '    "speed": %s,\n' "$(json_null_or_string "${speed}")"
    printf '    "ipv4": [],\n'
    printf '    "ipv6": []\n'
    printf '  }'
  done
  printf '\n]\n'
}

# ---------------------------------------------------------------------------
# Human-readable output
# ---------------------------------------------------------------------------

print_human() {
  local machine_name="$1"
  local interfaces_json="$2"

  printf '# Network Capture — %s\n\n' "${machine_name}"

  if tool_available python3; then
    printf '%s' "${interfaces_json}" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print('## Network Interfaces\n')
print('| Interface | MAC | State | MTU | Speed | IPv4 | IPv6 |')
print('|---|---|---|---|---|---|---|')
for iface in data:
    name = iface.get('name', '?')
    mac = iface.get('mac', '')
    state = iface.get('state', '?')
    mtu = iface.get('mtu', '')
    speed = iface.get('speed', '') or ''
    ipv4 = ', '.join(iface.get('ipv4', [])) or '-'
    ipv6 = ', '.join(iface.get('ipv6', [])) or '-'
    if name == 'lo':
        continue
    print(f'| {name} | {mac} | {state} | {mtu} | {speed} | {ipv4} | {ipv6} |')
" 2>/dev/null || printf '%s\n' "${interfaces_json}"
  else
    printf '%s\n' "${interfaces_json}"
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

  local machine_name timestamp interfaces_json
  machine_name="${HOSTNAME:-unknown}"
  timestamp="$(date --iso-8601=seconds 2>/dev/null || date -u +'%Y-%m-%dT%H:%M:%SZ')"
  interfaces_json="$(collect_interfaces_json)"

  if [[ "${HUMAN_ONLY}" == true ]]; then
    print_human "${machine_name}" "${interfaces_json}"
    exit 0
  fi

  emit_json_object_start
  emit_json_field "timestamp" "$(json_string "${timestamp}")"
  emit_json_field "machine_name" "$(json_string "${machine_name}")"
  printf '  "interfaces": %s\n' "${interfaces_json}"
  emit_json_object_end

  if [[ -n "${OUTPUT_DIR}" ]]; then
    mkdir -p "${OUTPUT_DIR}"
    "$0" > "${OUTPUT_DIR}/network.json" 2>/dev/null || log_warn "Could not write network.json"
    "$0" --human > "${OUTPUT_DIR}/network-summary.md" 2>/dev/null || log_warn "Could not write network-summary.md"
    log_info "Network capture written to ${OUTPUT_DIR}/"
  fi
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
