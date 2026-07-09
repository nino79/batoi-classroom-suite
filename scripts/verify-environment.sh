#!/usr/bin/env bash
# verify-environment.sh — Collect environment metadata for Beta validation reports.
#
# Outputs a JSON object to stdout with keys: kernel, distribution, hypervisor,
# has_efi, cpu_cores, memory_mib, python_version, pip_version, git_version,
# tools (object with tool-name -> version-or-null entries), timestamp.
#
# Exit codes: 0 on success, 1 on failure to collect at least one major field.

set -euo pipefail
IFS=$'\n\t'

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

json_string() {
  # Escape a value for JSON and emit it as a quoted string.
  local value="$1"
  # Escape backslash, quote, newline, tab, carriage-return.
  value="${value//\\/\\\\}"
  value="${value//\"/\\\"}"
  value="${value//$'\n'/\\n}"
  value="${value//$'\t'/\\t}"
  value="${value//$'\r'/\\r}"
  printf '"%s"' "${value}"
}

json_null_or_string() {
  if [[ -z "$1" ]]; then
    printf 'null'
  else
    json_string "$1"
  fi
}

detect_hypervisor() {
  # Returns the hypervisor name, or "none" if bare metal, or "unknown".
  if command -v systemd-detect-virt &>/dev/null; then
    systemd-detect-virt 2>/dev/null || echo "unknown"
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

check_tool() {
  # Print the version string for a tool, or "null".
  local tool="$1"
  if ! command -v "${tool}" &>/dev/null; then
    printf 'null'
    return
  fi
  case "${tool}" in
    bcs)
      bcs --version 2>/dev/null | head -1 || printf 'null'
      ;;
    efibootmgr)
      efibootmgr --version 2>/dev/null | head -1 || printf 'null'
      ;;
    mokutil)
      mokutil --version 2>/dev/null | head -1 || printf 'null'
      ;;
    lsblk)
      lsblk --version 2>/dev/null | head -1 || printf 'null'
      ;;
    blkid)
      blkid --version 2>/dev/null | head -1 || printf 'null'
      ;;
    findmnt)
      findmnt --version 2>/dev/null | head -1 || printf 'null'
      ;;
    df)
      df --version 2>/dev/null | head -1 || printf 'null'
      ;;
    ip)
      ip --version 2>/dev/null 2>&1 | head -1 || printf 'null'
      ;;
    dmidecode)
      dmidecode --version 2>/dev/null | head -1 || printf 'null'
      ;;
    python3)
      python3 --version 2>/dev/null | head -1 || printf 'null'
      ;;
    pip3)
      pip3 --version 2>/dev/null | head -1 || printf 'null'
      ;;
    git)
      git --version 2>/dev/null | head -1 || printf 'null'
      ;;
    *)
      # Generic fallback: tool --version
      "${tool}" --version 2>/dev/null | head -1 || printf 'null'
      ;;
  esac
}

# ---------------------------------------------------------------------------
# Collection
# ---------------------------------------------------------------------------

collect_kernel() {
  uname -a 2>/dev/null || echo "unknown"
}

collect_distribution() {
  if [[ -f /etc/os-release ]]; then
    local id version
    id="$(grep -oP '(?<=^ID=).*' /etc/os-release | tr -d '"' 2>/dev/null || echo "unknown")"
    version="$(grep -oP '(?<=^VERSION_ID=).*' /etc/os-release | tr -d '"' 2>/dev/null || echo "unknown")"
    printf '%s %s' "${id}" "${version}"
  elif command -v lsb_release &>/dev/null; then
    lsb_release -ds 2>/dev/null | tr -d '"' || echo "unknown"
  else
    echo "unknown"
  fi
}

collect_has_efi() {
  if [[ -d /sys/firmware/efi ]]; then
    printf 'true'
  else
    printf 'false'
  fi
}

collect_cpu_cores() {
  nproc 2>/dev/null || grep -c ^processor /proc/cpuinfo 2>/dev/null || echo "0"
}

collect_memory_mib() {
  local total_kb
  total_kb="$(grep -oP '(?<=^MemTotal:)\s*[0-9]+' /proc/meminfo 2>/dev/null | tr -d ' ' || true)"
  if [[ -n "${total_kb}" ]]; then
    printf '%d' $(( total_kb / 1024 ))
  else
    echo "0"
  fi
}

collect_timestamp_iso() {
  date --iso-8601=seconds 2>/dev/null || date -u +"%Y-%m-%dT%H:%M:%SZ"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

main() {
  local kernel distribution hypervisor has_efi
  local cpu_cores memory_mib python_version pip_version git_version
  local timestamp

  kernel="$(collect_kernel)"
  distribution="$(collect_distribution)"
  hypervisor="$(detect_hypervisor)"
  has_efi="$(collect_has_efi)"
  cpu_cores="$(collect_cpu_cores)"
  memory_mib="$(collect_memory_mib)"
  timestamp="$(collect_timestamp_iso)"

  # Tool versions
  python_version="$(check_tool python3)"
  pip_version="$(check_tool pip3)"
  git_version="$(check_tool git)"

  # Emit JSON
  printf '{\n'
  printf '  "timestamp": %s,\n' "$(json_string "${timestamp}")"
  printf '  "kernel": %s,\n' "$(json_string "${kernel}")"
  printf '  "distribution": %s,\n' "$(json_string "${distribution}")"
  printf '  "hypervisor": %s,\n' "$(json_string "${hypervisor}")"
  printf '  "has_efi": %s,\n' "${has_efi}"
  printf '  "cpu_cores": %s,\n' "${cpu_cores}"
  printf '  "memory_mib": %s,\n' "${memory_mib}"
  printf '  "python_version": %s,\n' "$(json_null_or_string "${python_version}")"
  printf '  "pip_version": %s,\n' "$(json_null_or_string "${pip_version}")"
  printf '  "git_version": %s,\n' "$(json_null_or_string "${git_version}")"
  printf '  "tools": {\n'
  local first=1
  for tool in bcs efibootmgr mokutil lsblk blkid findmnt df ip dmidecode; do
    if [[ ${first} -eq 0 ]]; then
      printf ',\n'
    fi
    first=0
    local version
    version="$(check_tool "${tool}")"
    printf '    %s: %s' "$(json_string "${tool}")" "$(json_null_or_string "${version}")"
  done
  printf '\n  }\n'
  printf '}\n'
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
