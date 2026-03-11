#!/usr/bin/env bash
# run_semgrep - Run Semgrep with repo-local Python and Bash rules.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=../security/common.sh
source "${REPO_ROOT}/linting/security/common.sh"
source "${REPO_ROOT}/linting/config/semgrep.sh"

# semgrep_args - Build the configured Semgrep flags, excludes, and configs.
semgrep_args() {
  local args=()
  local exclude
  local rule_file
  local ruleset

  for value in "${SEMGREP_FLAGS[@]}"; do
    args+=("${value}")
  done
  for exclude in "${SEMGREP_EXCLUDES[@]}"; do
    args+=(--exclude "${exclude}")
  done
  for ruleset in "${SEMGREP_REGISTRY_RULESETS[@]}"; do
    args+=(--config "${ruleset}")
  done
  for rule_file in "${SEMGREP_LOCAL_RULE_FILES[@]}"; do
    args+=(--config "${REPO_ROOT}/${rule_file}")
  done

  printf '%s\n' "${args[@]}"
}

# run_semgrep_local - Run Semgrep locally when the CLI is installed.
run_semgrep_local() {
  local args=()
  while IFS= read -r arg; do
    args+=("${arg}")
  done < <(semgrep_args)

  semgrep "${args[@]}" "${SEMGREP_TARGETS[@]}"
}

# run_semgrep_docker - Run Semgrep inside Docker when the CLI is unavailable.
run_semgrep_docker() {
  local args=()
  local target
  local docker_targets=()
  while IFS= read -r arg; do
    args+=("${arg}")
  done < <(semgrep_args)
  for target in "${SEMGREP_TARGETS[@]}"; do
    docker_targets+=("/src/${target}")
  done

  docker run --rm \
    -v "${REPO_ROOT}:/src" \
    "${SEMGREP_IMAGE}" \
    semgrep \
    "${args[@]}" \
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
