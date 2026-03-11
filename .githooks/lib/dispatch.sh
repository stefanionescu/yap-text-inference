#!/usr/bin/env bash
# Shared dispatch helpers for thin hook stage wrappers.

set -euo pipefail

ROOT_DIR="${ROOT_DIR:-$(git rev-parse --show-toplevel)}"

# shellcheck disable=SC1091  # lint:justify -- reason: sourced relative hook runtime helper -- ticket: N/A
source "${ROOT_DIR}/.githooks/lib/runtime.sh"

# enter_repo_root - Switch to the repository root for stage execution.
enter_repo_root() {
  cd "${ROOT_DIR}"
}

# run_global_stage - Execute a global hook stage for the requested mode.
run_global_stage() {
  local stage="$1"
  shift
  local mode
  mode="$(parse_hook_mode "${1:-commit}")"

  enter_repo_root

  case "${stage}:${mode}" in
    lint:commit)
      bash linting/docs/run.sh
      ;;
    security:commit)
      local staged_envs=""
      staged_envs="$(staged_files | grep -iE "${PROD_ENV_PATTERN}" || true)"
      if [[ -n ${staged_envs} ]]; then
        echo "Production environment files are staged:" >&2
        echo "${staged_envs}" >&2
        echo "Remove them from the index or bypass with SKIP_ENV_CHECK=1." >&2
        exit 1
      fi
      ;;
    *)
      die_hook_error "unsupported global hook stage: ${stage}:${mode}"
      ;;
  esac
}

# run_project_stage - Execute a project-scoped hook stage for the requested mode.
run_project_stage() {
  local stage="$1"
  shift
  local mode
  mode="$(parse_hook_mode "${1:-commit}")"

  enter_repo_root

  case "${stage}:${mode}" in
    python:commit)
      bash linting/lint.sh --only code
      ;;
    shell:commit)
      bash linting/lint.sh --only shell
      ;;
    docker:commit)
      bash linting/lint.sh --only docker
      ;;
    quality:commit)
      bash linting/lint.sh --only quality
      ;;
    security:push)
      bash linting/security/run.sh
      ;;
    coverage:push)
      if [[ ${RUN_COVERAGE:-0} != "1" ]]; then
        echo "skip"
        return 0
      fi
      bash scripts/coverage.sh
      ;;
    *)
      die_hook_error "unsupported project hook stage: ${stage}:${mode}"
      ;;
  esac
}

# run_self_stage - Execute a .githooks self-check stage.
run_self_stage() {
  local stage="$1"

  enter_repo_root
  collect_hook_files_array
  if skip_when_no_files; then
    return 0
  fi

  case "${stage}" in
    lint)
      shellcheck -x -e SC1091 "${FILES[@]}"
      python linting/shell/run.py "${FILES[@]}"
      ;;
    format)
      shfmt -d -i 2 -ci -s "${FILES[@]}"
      ;;
    quality)
      python linting/structure/prefix_collisions.py .githooks
      python linting/structure/single_file_folders.py .githooks
      bunx jscpd --config "${HOOK_SELF_JSCPD_CONFIG}"
      ;;
    security)
      semgrep --error --no-rewrite-rule-ids --metrics=off --disable-version-check --config "${HOOK_SELF_SEMGREP_CONFIG}" "${FILES[@]}"
      ;;
    *)
      die_hook_error "unsupported self hook stage: ${stage}"
      ;;
  esac
}
