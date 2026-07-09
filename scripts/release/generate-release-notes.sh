#!/usr/bin/env bash
# generate-release-notes.sh — Generate release notes from CHANGELOG.md and
# git history, without publishing anything.
#
# Produces a structured Markdown document with:
#   - Version and release date
#   - Changes since last tag (from CHANGELOG [Unreleased] section)
#   - Git log summary (commits since last tag)
#   - Contributor acknowledgment
#   - Artifact checksums reference
#   - Upgrade notes (if any)
#
# Usage:
#   ./scripts/release/generate-release-notes.sh
#   ./scripts/release/generate-release-notes.sh --version 0.2.0-beta
#   ./scripts/release/generate-release-notes.sh --output /path/to/notes.md
#   ./scripts/release/generate-release-notes.sh --help
#
# Exit codes:
#   0 — Release notes generated
#   1 — Missing dependency

set -euo pipefail
IFS=$'\n\t'

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/_shared.sh"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

VERSION=""
OUTPUT_DIR="${PROJECT_ROOT}/reports/release"
OUTPUT_FILE=""
LAST_TAG=""

# ---------------------------------------------------------------------------
# Generation functions
# ---------------------------------------------------------------------------

find_last_tag() {
  if command -v git &>/dev/null; then
    git -C "${PROJECT_ROOT}" describe --tags --abbrev=0 2>/dev/null || echo ""
  else
    echo ""
  fi
}

get_commits_since_tag() {
  local tag="$1"
  local format="${2:-oneline}"

  if [[ -z "${tag}" ]]; then
    git -C "${PROJECT_ROOT}" log --oneline -20 2>/dev/null || true
  else
    git -C "${PROJECT_ROOT}" log "${tag}..HEAD" --oneline 2>/dev/null || true
  fi
}

get_commit_count_since_tag() {
  local tag="$1"
  if [[ -z "${tag}" ]]; then
    git -C "${PROJECT_ROOT}" rev-list --count HEAD 2>/dev/null || echo "0"
  else
    git -C "${PROJECT_ROOT}" rev-list --count "${tag}..HEAD" 2>/dev/null || echo "0"
  fi
}

get_contributors_since_tag() {
  local tag="$1"
  if [[ -z "${tag}" ]]; then
    git -C "${PROJECT_ROOT}" log --format='%aN' | sort -u 2>/dev/null || true
  else
    git -C "${PROJECT_ROOT}" log "${tag}..HEAD" --format='%aN' | sort -u 2>/dev/null || true
  fi
}

extract_unreleased() {
  local changelog="${PROJECT_ROOT}/CHANGELOG.md"
  if [[ ! -f "${changelog}" ]]; then
    return
  fi

  # Extract content between [Unreleased] and the next ## heading
  sed -n '/^## \[Unreleased\]/,/^## \[/p' "${changelog}" 2>/dev/null | head -n -1 | tail -n +3
}

get_commit_types() {
  local tag="$1"
  local type="$2"

  if command -v git &>/dev/null; then
    if [[ -z "${tag}" ]]; then
      git -C "${PROJECT_ROOT}" log --oneline --grep="^${type}:" 2>/dev/null || true
    else
      git -C "${PROJECT_ROOT}" log "${tag}..HEAD" --oneline --grep="^${type}:" 2>/dev/null || true
    fi
  fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

main() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --help|-h)
        print_usage_and_exit "$0" \
          "Generate release notes from CHANGELOG.md and git history." \
          "[--version <semver>] [--output <file>]" \
          "  0 — Release notes generated\n  1 — Missing dependency"
        ;;
      --version|-v)
        VERSION="$2"
        shift 2
        ;;
      --output|-o)
        OUTPUT_FILE="$2"
        shift 2
        ;;
      *)
        log_error "Unknown option: $1"
        printf 'Usage: %s [--version <semver>] [--output <file>]\n' "$0"
        exit 1
        ;;
    esac
  done

  # Determine version
  if [[ -z "${VERSION}" ]]; then
    VERSION="$(get_project_version)"
  fi

  # Determine last tag
  if command -v git &>/dev/null; then
    LAST_TAG="$(find_last_tag)"
  fi

  # Determine release date
  local release_date
  release_date="$(date --iso-8601=seconds 2>/dev/null || date -u +'%Y-%m-%dT%H:%M:%SZ')"

  # Count commits
  local commit_count
  commit_count="$(get_commit_count_since_tag "${LAST_TAG}")"

  # Determine if this is a Beta release
  local is_beta=false
  if [[ "${VERSION}" == *"beta"* ]] || [[ "${VERSION}" == 0.* ]]; then
    is_beta=true
  fi

  # Generate notes
  local notes
  notes="$(
    printf '# Batoi Classroom Suite — v%s\n\n' "${VERSION}"

    if [[ "${is_beta}" == true ]]; then
      printf '**Beta release** — %s  \n' "${release_date}"
    else
      printf '**Release date:** %s  \n' "${release_date}"
    fi

    if [[ -n "${LAST_TAG}" ]]; then
      printf '**Previous release:** %s  \n' "${LAST_TAG}"
    fi
    printf '**Commits since last tag:** %s  \n\n' "${commit_count}"

    # --- What's New ---
    printf '## What'\''s New\n\n'

    local unreleased
    unreleased="$(extract_unreleased)"
    if [[ -n "${unreleased}" ]]; then
      printf '%s\n\n' "${unreleased}"
    else
      printf '_No unreleased changes documented._\n\n'
    fi

    # --- Changelog by type ---
    if command -v git &>/dev/null; then
      printf '## Commit Summary\n\n'

      local -a types=("feat" "fix" "docs" "refactor" "chore" "test" "adr")
      local -a labels=("Features" "Bug Fixes" "Documentation" "Refactoring" "Maintenance" "Testing" "Architecture Decisions")

      for i in "${!types[@]}"; do
        local type="${types[$i]}"
        local label="${labels[$i]}"
        local commits
        commits="$(get_commit_types "${LAST_TAG}" "${type}")"
        if [[ -n "${commits}" ]]; then
          printf '### %s\n\n' "${label}"
          printf '%s\n' "${commits}" | while IFS= read -r line; do
            local sha msg
            sha="$(printf '%s' "${line}" | cut -d' ' -f1)"
            msg="$(printf '%s' "${line}" | cut -d' ' -f2-)"
            printf '- %s ([%s](https://github.com/nino79/batoi-classroom-suite/commit/%s))\n' "${msg}" "${sha}" "${sha}"
          done
          printf '\n'
        fi
      done
    fi

    # --- Contributors ---
    printf '## Contributors\n\n'
    local contributors
    contributors="$(get_contributors_since_tag "${LAST_TAG}")"
    if [[ -n "${contributors}" ]]; then
      printf '%s\n' "${contributors}" | while IFS= read -r name; do
        printf '- %s\n' "${name}"
      done
    else
      printf '_No contributor data available._\n'
    fi
    printf '\n'

    # --- Artifacts ---
    printf '## Artifacts\n\n'
    printf '| File | SHA256 |\n'
    printf '|---|---|\n'
    local dist_dir="${PROJECT_ROOT}/dist"
    if [[ -d "${dist_dir}" ]]; then
      local checksum_file="${dist_dir}/SHA256SUMS.txt"
      if [[ -f "${checksum_file}" ]]; then
        while IFS= read -r line; do
          local sha filename
          sha="$(printf '%s' "${line}" | awk '{print $1}')"
          filename="$(printf '%s' "${line}" | awk '{print $2}')"
          printf '| %s | `%s` |\n' "${filename}" "${sha}"
        done < "${checksum_file}"
      else
        while IFS= read -r -d '' f; do
          local sha fname
          sha="$(sha256sum "${f}" | cut -d' ' -f1)"
          fname="$(basename "${f}")"
          printf '| %s | `%s` |\n' "${fname}" "${sha}"
        done < <(find "${dist_dir}" -maxdepth 1 -type f \( -name '*.whl' -o -name '*.tar.gz' \) -print0)
      fi
    else
      printf '| _No artifacts found_ | — |\n'
    fi
    printf '\n'

    # --- Upgrade Notes ---
    printf '## Upgrade Notes\n\n'
    if [[ "${is_beta}" == true ]]; then
      printf '> ⚠️ This is a pre-release version. APIs may change without notice.\n\n'
    fi
    printf '### Installation\n\n'
    printf '```bash\n'
    printf '# Install from PyPI (when published):\n'
    printf 'pip install bcs\n\n'
    printf '# Or install from wheel:\n'
    printf 'pip install bcs-*.whl\n'
    printf '```\n\n'

    printf '### Requirements\n\n'
    printf '- Python >= 3.12\n'
    printf '- Linux (Ubuntu 24.04 LTS recommended)\n'
    printf '- UEFI firmware (for full hardware detection)\n'
  )"

  # Write output
  mkdir -p "${OUTPUT_DIR}"
  if [[ -n "${OUTPUT_FILE}" ]]; then
    printf '%s\n' "${notes}" > "${OUTPUT_FILE}"
    log_info "Release notes written to ${OUTPUT_FILE}"
  else
    local default_file="${OUTPUT_DIR}/release-notes.md"
    printf '%s\n' "${notes}" > "${default_file}"
    log_info "Release notes written to ${default_file}"
  fi

  log_info "Release notes generated for v${VERSION}"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
