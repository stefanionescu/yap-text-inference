#!/usr/bin/env bash
# Shared helpers for staged git hook scripts.

set -euo pipefail

ROOT_DIR="${ROOT_DIR:-$(git rev-parse --show-toplevel)}"
GITHOOKS_DIR="${ROOT_DIR}/.githooks"

# shellcheck disable=SC1091  # lint:justify -- reason: sourced relative hook config helper -- ticket: N/A
source "${GITHOOKS_DIR}/lib/config.sh"
# shellcheck disable=SC1091  # lint:justify -- reason: sourced relative hook timeout helper -- ticket: N/A
source "${GITHOOKS_DIR}/lib/timeout.sh"

FILES=()

# die_hook_error - Print a normalized hook error and exit.
die_hook_error() {
  local message="$1"
  echo "error: ${message}" >&2
  exit 2
}

# require_tool - Abort when a CLI dependency is missing.
require_tool() {
  local tool="$1"
  local hint="$2"
  if ! command -v "${tool}" >/dev/null 2>&1; then
    echo "error: ${tool} is required (${hint})" >&2
    exit 1
  fi
}

# parse_hook_mode - Normalize hook mode arguments to commit or push.
parse_hook_mode() {
  case "${1:-commit}" in
    --mode=commit | commit) echo "commit" ;;
    --mode=push | --mode=pre-push | push | pre-push) echo "push" ;;
    *) die_hook_error "unsupported hook mode: ${1:-}" ;;
  esac
}

# staged_files - Emit staged repo-relative files for commit-time hooks.
staged_files() {
  git diff --cached --name-only --diff-filter=ACMR
}

# repo_files - Emit tracked repo-relative files for full-repo hook stages.
repo_files() {
  git ls-files
}

# append_matching_file - Add a repo-relative file to FILES when it matches a regex.
append_matching_file() {
  local regex="$1"
  local path="$2"
  [[ -n ${path} ]] || return 0
  [[ ${path} =~ ${regex} ]] || return 0
  [[ -f "${ROOT_DIR}/${path}" ]] || return 0
  FILES+=("${path}")
}

# emit_mode_files - Emit repo-relative files for a hook mode.
emit_mode_files() {
  case "$1" in
    commit) staged_files ;;
    push) repo_files ;;
    *) die_hook_error "unsupported collect mode: $1" ;;
  esac
}

# collect_mode_files - Populate FILES with mode-specific files matching a regex.
collect_mode_files() {
  local mode="$1"
  local regex="$2"
  local path
  FILES=()

  while IFS= read -r path; do
    append_matching_file "${regex}" "${path}"
  done < <(emit_mode_files "${mode}")
}

# collect_hook_files_array - Populate FILES with tracked hook entrypoints and scripts.
collect_hook_files_array() {
  local path
  FILES=()
  while IFS= read -r path; do
    append_matching_file "${HOOK_FILE_PATTERN}" "${path}"
  done < <(git ls-files | grep -E "${HOOK_FILE_PATTERN}" || true)
}

# skip_when_no_files - Emit the standard skip marker when FILES is empty.
skip_when_no_files() {
  if [[ ${#FILES[@]} -eq 0 ]]; then
    echo "skip"
    return 0
  fi
  return 1
}

# run_hook_no_stdin - Run a hook script with timeout and buffered output.
run_hook_no_stdin() {
  local name="$1"
  local skip_var="$2"
  local timeout_seconds="$3"
  local script="$4"
  shift 4

  local should_skip="${!skip_var-0}"
  if [[ ${should_skip} == "1" ]]; then
    return 0
  fi
  if [[ ! -x ${script} ]]; then
    return 0
  fi

  local output=""
  local status=0
  if ! output="$(run_with_timeout "${timeout_seconds}" "${script}" "$@" 2>&1)"; then
    status=$?
    if [[ ${output} != "skip" ]]; then
      echo -e "${RED}${name}${NC}"
      [[ -n ${output} ]] && echo "${output}"
      # shellcheck disable=SC2034  # lint:justify -- reason: FAILED is shared with the sourcing hook entrypoint -- ticket: N/A
      FAILED=1
    fi
    return "${status}"
  fi

  return 0
}
