#!/usr/bin/env bash
# run_semgrep - Run Semgrep with repo-local Python and Bash rules.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=../security/common.sh
source "${REPO_ROOT}/linting/security/common.sh"
source "${REPO_ROOT}/linting/config/semgrep/env.sh"
CONFIG_OVERRIDES=()
TARGET_OVERRIDES=()

# usage - Print CLI usage.
usage() {
  cat <<'USAGE'
Usage: linting/semgrep/run.sh [--config <config>]... [--target <path>]...

Runs Semgrep with repo-local defaults unless one or more explicit configs/targets are provided.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --config)
      CONFIG_OVERRIDES+=("${2:-}")
      shift 2
      ;;
    --target)
      TARGET_OVERRIDES+=("${2:-}")
      shift 2
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

# semgrep_args - Build the configured Semgrep flags, excludes, and configs.
semgrep_args() {
  local args=()
  local config_value
  local exclude
  local rule_file
  local ruleset

  for value in "${SEMGREP_FLAGS[@]}"; do
    args+=("${value}")
  done
  for exclude in "${SEMGREP_EXCLUDES[@]}"; do
    args+=(--exclude "${exclude}")
  done
  if [[ ${#CONFIG_OVERRIDES[@]} -gt 0 ]]; then
    for config_value in "${CONFIG_OVERRIDES[@]}"; do
      if [[ -f ${config_value} ]]; then
        args+=(--config "${config_value}")
      elif [[ -f ${REPO_ROOT}/${config_value} ]]; then
        args+=(--config "${REPO_ROOT}/${config_value}")
      else
        args+=(--config "${config_value}")
      fi
    done
  else
    for ruleset in "${SEMGREP_REGISTRY_RULESETS[@]}"; do
      args+=(--config "${ruleset}")
    done
    for rule_file in "${SEMGREP_LOCAL_RULE_FILES[@]}"; do
      args+=(--config "${REPO_ROOT}/${rule_file}")
    done
  fi

  printf '%s\n' "${args[@]}"
}

# semgrep_targets - Emit the configured Semgrep targets.
semgrep_targets() {
  local target
  if [[ ${#TARGET_OVERRIDES[@]} -gt 0 ]]; then
    for target in "${TARGET_OVERRIDES[@]}"; do
      printf '%s\n' "${target}"
    done
    return 0
  fi
  for target in "${SEMGREP_TARGETS[@]}"; do
    printf '%s\n' "${target}"
  done
}

# run_semgrep_local - Run Semgrep locally when the CLI is installed.
run_semgrep_local() {
  local args=()
  local targets=()
  while IFS= read -r arg; do
    args+=("${arg}")
  done < <(semgrep_args)
  while IFS= read -r target; do
    targets+=("${target}")
  done < <(semgrep_targets)

  semgrep "${args[@]}" "${targets[@]}"
}

# run_semgrep_docker - Run Semgrep inside Docker when the CLI is unavailable.
run_semgrep_docker() {
  local args=()
  local target
  local docker_targets=()
  while IFS= read -r arg; do
    args+=("${arg}")
  done < <(semgrep_args)
  while IFS= read -r target; do
    docker_targets+=("/src/${target}")
  done < <(semgrep_targets)

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
