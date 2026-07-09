#!/usr/bin/env bash
# validate-beta.sh — Automated Beta validation for Batoi Classroom Suite.
#
# Orchestrates environment capture, CLI command execution, and report
# generation into reports/validation/.
#
# Usage:
#   ./scripts/validate-beta.sh                     # run from repository root
#   bash scripts/validate-beta.sh                  # same
#   VALIDATION_DIR=/tmp/my-report ./scripts/validate-beta.sh  # custom output dir
#
# Exit codes:
#   0 — All commands executed (individual failures recorded in report).
#   1 — Fatal error before any command could run (e.g. missing dependency).
#   2 — No bcs executable found.

set -euo pipefail
IFS=$'\n\t'

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Output directory; override via VALIDATION_DIR env var.
VALIDATION_DIR="${VALIDATION_DIR:-${PROJECT_ROOT}/reports/validation}"
readonly VALIDATION_DIR

# List of commands to validate.
declare -a COMMANDS=(
  "bcs version"
  "bcs --help"
  "bcs validate config/examples/default.yaml"
  "bcs inventory"
  "bcs inventory --output json"
  "bcs inventory --output yaml"
  "bcs doctor"
)

# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------

log_info()  { printf '[INFO]  %s\n' "$*" >&2; }
log_warn()  { printf '[WARN]  %s\n' "$*" >&2; }
log_error() { printf '[ERROR] %s\n' "$*" >&2; }

json_string() {
  local value="$1"
  value="${value//\\/\\\\}"
  value="${value//\"/\\\"}"
  value="${value//$'\n'/\\n}"
  value="${value//$'\t'/\\t}"
  value="${value//$'\r'/\\r}"
  printf '"%s"' "${value}"
}

duration_seconds() {
  local start_sec="$1"
  local end_sec="$2"
  # bc may not be installed; fall back to integer arithmetic.
  local diff=$(( end_sec - start_sec ))
  # Use python3 for sub-second precision if available.
  if command -v python3 &>/dev/null; then
    python3 -c "print(round(float('${end_sec}') - float('${start_sec}'), 3))" 2>/dev/null || printf '%d' "${diff}"
  else
    printf '%d' "${diff}"
  fi
}

now_epoch() {
  if command -v python3 &>/dev/null; then
    python3 -c "import time; print(time.time())" 2>/dev/null || printf '%s' "$(date +%s)"
  else
    date +%s
  fi
}

run_command() {
  local label="$1"
  local cmd="$2"
  local out_file="$3"
  local err_file="$4"
  local rc_file="$5"
  local time_file="$6"

  local start_time
  start_time="$(now_epoch)"

  set +e
  bash -c "${cmd}" > "${out_file}" 2>"${err_file}"
  local rc=$?
  set -e

  local end_time
  end_time="$(now_epoch)"

  printf '%d' "${rc}" > "${rc_file}"
  duration_seconds "${start_time}" "${end_time}" > "${time_file}"
}

ensure_executable() {
  local name="$1"
  if ! command -v "${name}" &>/dev/null; then
    log_error "${name} not found on PATH"
    return 1
  fi
}

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------

main() {
  log_info "BCS Beta Validation — $(date)"

  # Verify we are in the project root.
  if [[ ! -f "${PROJECT_ROOT}/cli/pyproject.toml" ]]; then
    log_error "Run this script from the repository root (${PROJECT_ROOT})"
    exit 1
  fi

  # Verify bcs is available.
  if ! ensure_executable "bcs"; then
    log_error "bcs executable not found. Ensure virtual environment is active and bcs is installed."
    exit 2
  fi

  # Verify virtual environment is active for bcs.
  local bcs_path
  bcs_path="$(command -v bcs)"
  if [[ "${bcs_path}" != *.venv* ]]; then
    log_warn "bcs is at ${bcs_path} — not inside a .venv, but continuing"
  fi

  # Record git revision.
  local git_revision="unknown"
  if command -v git &>/dev/null; then
    git_revision="$(git -C "${PROJECT_ROOT}" rev-parse --short HEAD 2>/dev/null || echo "unknown")"
  fi
  readonly git_revision

  # Create output directory.
  mkdir -p "${VALIDATION_DIR}"

  # -----------------------------------------------------------------------
  # 1. Environment capture
  # -----------------------------------------------------------------------
  log_info "Capturing environment…"
  local env_json="${VALIDATION_DIR}/environment.json"
  if [[ -x "${SCRIPT_DIR}/verify-environment.sh" ]]; then
    bash "${SCRIPT_DIR}/verify-environment.sh" > "${env_json}" 2>/dev/null
    log_info "Environment written to ${env_json}"
  else
    log_warn "verify-environment.sh not found; writing minimal environment"
    printf '{"timestamp": %s, "warning": "verify-environment.sh not available"}\n' \
      "$(json_string "$(date --iso-8601=seconds 2>/dev/null || date -u +'%Y-%m-%dT%H:%M:%SZ')")" \
      > "${env_json}"
  fi

  # -----------------------------------------------------------------------
  # 2. Execute CLI commands
  # -----------------------------------------------------------------------
  local start_overall end_overall
  start_overall="$(now_epoch)"
  local overall_rc=0
  declare -a results

  for cmd_spec in "${COMMANDS[@]}"; do
    # Build a safe label from the command.
    local label="${cmd_spec// /-}"
    label="${label//--/}"
    label="${label//\//_}"

    local out_file="${VALIDATION_DIR}/${label}_stdout.txt"
    local err_file="${VALIDATION_DIR}/${label}_stderr.txt"
    local rc_file="${VALIDATION_DIR}/${label}_rc.txt"
    local time_file="${VALIDATION_DIR}/${label}_time.txt"

    log_info "Running: ${cmd_spec}"
    run_command "${label}" "${cmd_spec}" "${out_file}" "${err_file}" "${rc_file}" "${time_file}"

    local rc duration_s
    rc="$(cat "${rc_file}")"
    duration_s="$(cat "${time_file}")"

    results+=("${cmd_spec}|${rc}|${duration_s}")

    if [[ "${rc}" -ne 0 ]]; then
      log_warn "  Exit code: ${rc}"
    fi
    log_info "  Duration: ${duration_s}s"
  done

  end_overall="$(now_epoch)"
  local total_duration
  total_duration="$(duration_seconds "${start_overall}" "${end_overall}")"

  # -----------------------------------------------------------------------
  # 3. Generate artifacts
  # -----------------------------------------------------------------------

  # --- timings.json ---
  local timings_json="${VALIDATION_DIR}/timings.json"
  {
    printf '{\n'
    printf '  "started_at": %s,\n' "$(json_string "$(date --iso-8601=seconds 2>/dev/null || date -u +'%Y-%m-%dT%H:%M:%SZ')")"
    printf '  "git_revision": %s,\n' "$(json_string "${git_revision}")"
    printf '  "total_duration_seconds": %s,\n' "${total_duration}"
    printf '  "commands": [\n'
    local first=1
    for entry in "${results[@]}"; do
      if [[ ${first} -eq 0 ]]; then
        printf ',\n'
      fi
      first=0
      local cmd rc dur
      IFS='|' read -r cmd rc dur <<< "${entry}"
      printf '    {"command": %s, "exit_code": %s, "duration_seconds": %s}' \
        "$(json_string "${cmd}")" "${rc}" "${dur}"
    done
    printf '\n  ]\n'
    printf '}\n'
  } > "${timings_json}"
  log_info "Timings written to ${timings_json}"

  # --- Copy named outputs ---
  if [[ -f "${VALIDATION_DIR}/bcs-inventory---output-json_stdout.txt" ]]; then
    cp "${VALIDATION_DIR}/bcs-inventory---output-json_stdout.txt" "${VALIDATION_DIR}/inventory.json"
    log_info "inventory.json copied"
  fi
  if [[ -f "${VALIDATION_DIR}/bcs-inventory---output-yaml_stdout.txt" ]]; then
    cp "${VALIDATION_DIR}/bcs-inventory---output-yaml_stdout.txt" "${VALIDATION_DIR}/inventory.yaml"
    log_info "inventory.yaml copied"
  fi
  if [[ -f "${VALIDATION_DIR}/bcs-doctor_stdout.txt" ]]; then
    cp "${VALIDATION_DIR}/bcs-doctor_stdout.txt" "${VALIDATION_DIR}/doctor.txt"
    log_info "doctor.txt copied"
  fi

  # --- report.md ---
  local report_md="${VALIDATION_DIR}/report.md"
  {
    printf '# Beta Validation Report\n\n'
    printf '**Generated:** %s  \n' "$(date --iso-8601=seconds 2>/dev/null || date -u +'%Y-%m-%dT%H:%M:%SZ')"
    printf '**Git revision:** %s  \n' "${git_revision}"
    printf '**Total duration:** %ss  \n\n' "${total_duration}"
    printf '## Command Results\n\n'
    printf '| Command | Exit Code | Duration (s) |\n'
    printf '|---|---|---|\n'
    for entry in "${results[@]}"; do
      local cmd rc dur
      IFS='|' read -r cmd rc dur <<< "${entry}"
      local status_icon="✅"
      if [[ "${rc}" -ne 0 ]]; then
        status_icon="❌"
      fi
      printf '| %s \`%s\` | %s %d | %s |\n' "${status_icon}" "${cmd}" "${status_icon}" "${rc}" "${dur}"
    done
    printf '\n## Files\n\n'
    printf '| File | Description |\n'
    printf '|---|---|\n'
    printf '| environment.json | Host environment metadata |\n'
    printf '| inventory.json | bcs inventory --output json |\n'
    printf '| inventory.yaml | bcs inventory --output yaml |\n'
    printf '| doctor.txt | bcs doctor output |\n'
    printf '| timings.json | Command execution times and exit codes |\n'
    for cmd_spec in "${COMMANDS[@]}"; do
      local label="${cmd_spec// /-}"
      label="${label//--/}"
      label="${label//\//_}"
      printf '| %s_stdout.txt | stdout for \`%s\` |\n' "${label}" "${cmd_spec}"
      printf '| %s_stderr.txt | stderr for \`%s\` |\n' "${label}" "${cmd_spec}"
    done
  } > "${report_md}"
  log_info "Report written to ${report_md}"

  # -----------------------------------------------------------------------
  # Summary
  # -----------------------------------------------------------------------
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
  local total=$(( passed + failed ))

  printf '\n'
  log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  log_info "Validation complete — ${passed}/${total} passed, ${failed} failed"
  log_info "Total time: ${total_duration}s"
  log_info "Reports: ${VALIDATION_DIR}/"
  log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  if [[ "${failed}" -gt 0 ]]; then
    overall_rc=1
  fi

  exit "${overall_rc}"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
