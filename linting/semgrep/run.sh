#!/usr/bin/env bash
# run_semgrep - Run Semgrep with repo-local Python and Bash rules.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=../security/common.sh
source "${REPO_ROOT}/linting/security/common.sh"
source_security_config "semgrep"

# run_semgrep_local - Run Semgrep locally when the CLI is installed.
run_semgrep_local() {
  local args=(
    --error
    --no-rewrite-rule-ids
    --metrics=off
    --disable-version-check
  )
  local exclude
  for exclude in "${SEMGREP_EXCLUDES[@]}"; do
    args+=(--exclude "${exclude}")
  done

  semgrep \
    "${args[@]}" \
    --config "${REPO_ROOT}/${SEMGREP_RULES_FILE}" \
    "${SEMGREP_TARGETS[@]}"
}

# run_semgrep_docker - Run Semgrep inside Docker when the CLI is unavailable.
run_semgrep_docker() {
  local args=(
    --error
    --no-rewrite-rule-ids
    --metrics=off
    --disable-version-check
  )
  local exclude
  local target
  local docker_targets=()
  for exclude in "${SEMGREP_EXCLUDES[@]}"; do
    args+=(--exclude "${exclude}")
  done
  for target in "${SEMGREP_TARGETS[@]}"; do
    docker_targets+=("/src/${target}")
  done

  docker run --rm \
    -v "${REPO_ROOT}:/src" \
    "${SEMGREP_IMAGE}" \
    semgrep \
    "${args[@]}" \
    --config "/src/${SEMGREP_RULES_FILE}" \
    "${docker_targets[@]}"
}

cd "${REPO_ROOT}"

if command -v semgrep >/dev/null 2>&1; then
  run_semgrep_local
  exit 0
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "error: semgrep is not installed and Docker is unavailable" >&2
  exit 1
fi

run_semgrep_docker
