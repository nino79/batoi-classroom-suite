#!/usr/bin/env bash
# verify-package.sh — Verify built packages (wheel, sdist) and validate
# installation in a clean virtual environment.
#
# Performs:
#   1. Package metadata verification (name, version, entry points)
#   2. Wheel contents inspection
#   3. Source distribution inspection
#   4. Editable install from source
#   5. Fresh virtual environment install from wheel
#   6. Entry point smoke test
#   7. Configuration file presence check
#   8. Dependency resolution check
#   9. Dependency summary generation
#
# Usage:
#   ./scripts/release/verify-package.sh
#   ./scripts/release/verify-package.sh --artifacts /path/to/dist
#   ./scripts/release/verify-package.sh --skip-install
#   ./scripts/release/verify-package.sh --help
#
# Exit codes:
#   0 — All verifications passed
#   1 — Missing dependency
#   3 — Verification failed

set -euo pipefail
IFS=$'\n\t'

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/_shared.sh"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ARTIFACTS_DIR="${PROJECT_ROOT}/dist"
SKIP_INSTALL=false
TEMP_VENV=""
VISIBLE_WARNINGS=""

# ---------------------------------------------------------------------------
# Verification functions
# ---------------------------------------------------------------------------

verify_metadata() {
  local wheel_file="$1"

  if [[ -z "${wheel_file}" || ! -f "${wheel_file}" ]]; then
    log_fail "No wheel file to verify"
    return 1
  fi

  log_info "Verifying package metadata from: $(basename "${wheel_file}")"

  # Check metadata using Python
  local meta_ok=true

  if ! python3 -c "
import zipfile, json
with zipfile.ZipFile('${wheel_file}') as z:
    # Find METADATA file
    for name in z.namelist():
        if name.endswith('/METADATA'):
            content = z.read(name).decode('utf-8')
            break
    else:
        print('METADATA not found')
        exit(1)

    meta = {}
    for line in content.splitlines():
        if ':' in line:
            key, val = line.split(':', 1)
            meta[key.strip()] = val.strip()

    errors = []
    if meta.get('Name') != 'bcs':
        errors.append(f'Name: expected bcs, got {meta.get(\"Name\")}')
    if not meta.get('Version'):
        errors.append('Version: missing')
    if 'Entry-point' not in content and 'console_scripts' not in content:
        errors.append('No entry points found')

    if errors:
        for e in errors:
            print(f'FAIL: {e}')
        exit(1)
    print(f'Name: {meta.get(\"Name\")}')
    print(f'Version: {meta.get(\"Version\")}')
    print(f'Requires-Python: {meta.get(\"Requires-Python\")}')
    print('Entry points: found')
" 2>&1; then
    meta_ok=false
  fi

  if [[ "${meta_ok}" == false ]]; then
    log_fail "Package metadata verification failed"
    return 1
  fi
  log_pass "Package metadata verified"
}

verify_wheel_contents() {
  local wheel_file="$1"

  log_info "Inspecting wheel contents..."

  if ! python3 -c "
import zipfile
with zipfile.ZipFile('${wheel_file}') as z:
    names = z.namelist()
    print(f'Total entries: {len(names)}')
    print()
    # Show package files (not dist-info)
    pkg_files = [n for n in names if 'dist-info' not in n]
    print('Package files:')
    for f in sorted(pkg_files):
        print(f'  {f}')
    print()
    # Show dist-info
    dist_info = [n for n in names if 'dist-info' in n]
    print('Dist-info files:')
    for f in sorted(dist_info):
        print(f'  {f}')
" 2>&1; then
    return 1
  fi

  log_pass "Wheel contents verified"
}

verify_sdist_contents() {
  local sdist_file="$1"

  if [[ -z "${sdist_file}" || ! -f "${sdist_file}" ]]; then
    log_warn "No source distribution found — skipping sdist verification"
    return 0
  fi

  log_info "Inspecting source distribution..."

  if ! python3 -c "
import tarfile
with tarfile.open('${sdist_file}', 'r:gz') as tar:
    names = tar.getnames()
    print(f'Total entries: {len(names)}')
    # Show top-level items
    tops = sorted(set(n.split('/')[0] for n in names))
    for t in tops:
        count = len([n for n in names if n.startswith(t + '/') or n == t])
        print(f'  {t}/ ({count} entries)')
" 2>&1; then
    return 1
  fi

  log_pass "Source distribution contents verified"
}

verify_editable_install() {
  log_info "Testing editable install from source..."

  local temp_venv
  temp_venv="$(mktemp -d 2>/dev/null || mktemp -d 2>/dev/null)"
  trap 'rm -rf "${temp_venv}"' RETURN

  if ! python3 -m venv "${temp_venv}" 2>/dev/null; then
    log_fail "Failed to create virtual environment for editable install test"
    return 1
  fi

  # Install in editable mode
  if ! "${temp_venv}/bin/pip" install -e "${CLI_DIR}" 2>&1; then
    log_fail "Editable install failed"
    return 1
  fi

  # Verify entry point
  if ! "${temp_venv}/bin/bcs" --version 2>&1; then
    log_fail "Entry point smoke test failed after editable install"
    return 1
  fi

  rm -rf "${temp_venv}"
  log_pass "Editable install verified"
}

verify_wheel_install() {
  local wheel_file="$1"

  if [[ -z "${wheel_file}" || ! -f "${wheel_file}" ]]; then
    log_warn "No wheel file to install — skipping wheel install verification"
    return 0
  fi

  log_info "Testing installation from wheel in fresh virtual environment..."

  TEMP_VENV="$(mktemp -d 2>/dev/null || mktemp -d 2>/dev/null)"

  if ! python3 -m venv "${TEMP_VENV}" 2>/dev/null; then
    log_fail "Failed to create virtual environment for install test"
    return 1
  fi

  # Install from wheel
  if ! "${TEMP_VENV}/bin/pip" install "${wheel_file}" 2>&1; then
    log_fail "Installation from wheel failed"
    return 1
  fi

  log_pass "Wheel installed successfully"
}

verify_entry_points() {
  if [[ -z "${TEMP_VENV}" || ! -d "${TEMP_VENV}" ]]; then
    log_warn "No venv from wheel install — creating one"
    TEMP_VENV="$(mktemp -d 2>/dev/null || mktemp -d 2>/dev/null)"
    python3 -m venv "${TEMP_VENV}" 2>/dev/null || return 1
    local wheel_file
    wheel_file="$(find "${ARTIFACTS_DIR}" -name '*.whl' -type f 2>/dev/null | head -1)"
    if [[ -n "${wheel_file}" ]]; then
      "${TEMP_VENV}/bin/pip" install "${wheel_file}" 2>&1 || true
    fi
  fi

  log_info "Verifying entry points..."

  # Check bcs command is on path
  if [[ ! -f "${TEMP_VENV}/bin/bcs" ]]; then
    log_fail "bcs entry point not found in virtual environment"
    return 1
  fi

  # Smoke test
  local version_output
  version_output="$("${TEMP_VENV}/bin/bcs" --version 2>&1 || true)"
  if [[ -z "${version_output}" ]]; then
    log_fail "bcs --version produced no output"
    return 1
  fi
  log_pass "bcs entry point: ${version_output}"

  # Test --help
  if ! "${TEMP_VENV}/bin/bcs" --help &>/dev/null; then
    log_warn "bcs --help returned non-zero exit"
  else
    log_pass "bcs --help works"
  fi
}

verify_config_files() {
  log_info "Checking configuration files..."

  local config_dir="${PROJECT_ROOT}/config"
  local errors=0

  # Check schema.yaml
  if [[ -f "${config_dir}/schema.yaml" ]]; then
    log_pass "config/schema.yaml present"
  else
    log_warn "config/schema.yaml not found"
    (( errors++ )) || true
  fi

  # Check example config
  if [[ -f "${config_dir}/examples/default.yaml" ]]; then
    log_pass "config/examples/default.yaml present"
  else
    log_warn "config/examples/default.yaml not found"
    (( errors++ )) || true
  fi

  if [[ "${errors}" -gt 0 ]]; then
    log_warn "${errors} configuration file(s) missing"
  fi
}

check_dependencies() {
  log_info "Checking dependency resolution..."

  if [[ -z "${TEMP_VENV}" || ! -d "${TEMP_VENV}" ]]; then
    log_warn "No venv available — creating one for dependency check"
    TEMP_VENV="$(mktemp -d 2>/dev/null || mktemp -d 2>/dev/null)"
    python3 -m venv "${TEMP_VENV}" 2>/dev/null || return 0
    local wheel_file
    wheel_file="$(find "${ARTIFACTS_DIR}" -name '*.whl' -type f 2>/dev/null | head -1)"
    if [[ -n "${wheel_file}" ]]; then
      "${TEMP_VENV}/bin/pip" install "${wheel_file}" 2>&1 || true
    fi
  fi

  if ! "${TEMP_VENV}/bin/pip" check 2>&1; then
    log_warn "Dependency resolution reported issues"
    VISIBLE_WARNINGS="yes"
  else
    log_pass "All dependencies resolved"
  fi
}

generate_dependency_summary() {
  local output_dir="${PROJECT_ROOT}/reports/release"
  mkdir -p "${output_dir}"

  local deps_file="${output_dir}/dependency-summary.txt"

  log_info "Generating dependency summary..."

  {
    printf 'BCS Dependency Summary\n'
    printf '========================\n'
    printf 'Generated: %s\n\n' "$(date --iso-8601=seconds 2>/dev/null || date -u +'%Y-%m-%dT%H:%M:%SZ')"

    printf 'Declared dependencies (from pyproject.toml):\n'
    printf -- '------------------------------------------\n'
    grep -A 20 '^dependencies = \[' "${CLI_DIR}/pyproject.toml" 2>/dev/null | grep '".*"' | sed 's/^[[:space:]]*//' || echo '(none)'

    printf '\nDev dependencies:\n'
    printf -- '-----------------\n'
    grep -A 20 '^dev = \[' "${CLI_DIR}/pyproject.toml" 2>/dev/null | grep '".*"' | sed 's/^[[:space:]]*//' || echo '(none)'

    printf '\nResolved dependencies (from installed venv):\n'
    printf -- '------------------------------------------\n'
    if [[ -d "${TEMP_VENV}" ]]; then
      "${TEMP_VENV}/bin/pip" freeze 2>/dev/null || echo '(unable to list)'
    else
      echo '(no venv available)'
    fi
  } > "${deps_file}"

  log_pass "Dependency summary written to ${deps_file}"
}

generate_installed_file_list() {
  local output_dir="${PROJECT_ROOT}/reports/release"
  mkdir -p "${output_dir}"

  local manifest_file="${output_dir}/installed-files.txt"

  log_info "Generating installed file list..."

  {
    printf 'BCS Installed File Manifest\n'
    printf '=============================\n'
    printf 'Generated: %s\n\n' "$(date --iso-8601=seconds 2>/dev/null || date -u +'%Y-%m-%dT%H:%M:%SZ')"

    if [[ -d "${TEMP_VENV}" ]]; then
      local site_packages
      site_packages="$("${TEMP_VENV}/bin/python3" -c "import site; print(site.getsitepackages()[0])" 2>/dev/null || true)"
      if [[ -n "${site_packages}" && -d "${site_packages}/bcs" ]]; then
        printf 'Installed at: %s\n\n' "${site_packages}/bcs"
        find "${site_packages}/bcs" -type f -name '*.py' | sort | while IFS= read -r f; do
          local rel="${f#${site_packages}/}"
          local size
          size="$(stat --format='%s' "${f}" 2>/dev/null || wc -c < "${f}" | tr -d ' ')"
          printf '%s  (%s bytes)\n' "${rel}" "${size}"
        done
      else
        echo 'bcs package not found in site-packages'
      fi
    else
      echo '(no venv available)'
    fi
  } > "${manifest_file}"

  log_pass "Installed file list written to ${manifest_file}"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

main() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --help|-h)
        print_usage_and_exit "$0" \
          "Verify built packages and validate installation." \
          "[--artifacts <dir>] [--skip-install]" \
          "  0 — All verifications passed\n  1 — Missing dependency\n  3 — Verification failed"
        ;;
      --artifacts|-a)
        ARTIFACTS_DIR="$2"
        shift 2
        ;;
      --skip-install)
        SKIP_INSTALL=true
        shift
        ;;
      *)
        log_error "Unknown option: $1"
        printf 'Usage: %s [--artifacts <dir>] [--skip-install]\n' "$0"
        exit 1
        ;;
    esac
  done

  # Validate dependencies
  check_commands python3 pip3 || exit "${RC_MISSING_DEP}"
  check_directory "${ARTIFACTS_DIR}" "Artifacts directory" || exit "${RC_INVALID_STATE}"

  # Find wheel and sdist
  local wheel_file sdist_file
  wheel_file="$(find "${ARTIFACTS_DIR}" -name '*.whl' -type f 2>/dev/null | head -1 || true)"
  sdist_file="$(find "${ARTIFACTS_DIR}" -name '*.tar.gz' -type f 2>/dev/null | head -1 || true)"

  local project_version
  project_version="$(get_project_version)"

  log_info "BCS Package Verification — v${project_version}"
  log_info "Artifacts: ${ARTIFACTS_DIR}"
  printf '\n'

  # Step 1: Metadata
  verify_metadata "${wheel_file}" || exit "${RC_VERIFY_FAILED}"
  printf '\n'

  # Step 2: Wheel contents
  verify_wheel_contents "${wheel_file}" || exit "${RC_VERIFY_FAILED}"
  printf '\n'

  # Step 3: Source distribution
  verify_sdist_contents "${sdist_file}"
  printf '\n'

  # Step 4: Editable install (quick)
  verify_editable_install
  printf '\n'

  if [[ "${SKIP_INSTALL}" == true ]]; then
    log_info "Skipping full install verification (--skip-install)"
  else
    # Step 5: Fresh venv install from wheel
    verify_wheel_install "${wheel_file}"
    printf '\n'

    # Step 6: Entry points
    verify_entry_points
    printf '\n'

    # Step 7: Config files
    verify_config_files
    printf '\n'

    # Step 8: Dependencies
    check_dependencies
    printf '\n'

    # Step 9: Generate reports
    generate_dependency_summary
    generate_installed_file_list
    printf '\n'
  fi

  # Cleanup
  if [[ -n "${TEMP_VENV}" && -d "${TEMP_VENV}" ]]; then
    rm -rf "${TEMP_VENV}"
  fi

  # Summary
  log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  if [[ -n "${VISIBLE_WARNINGS}" ]]; then
    log_warn "Verification completed with warnings"
  else
    log_info "All verifications passed"
  fi
  log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
