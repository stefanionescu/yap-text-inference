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
      collect_mode_files "${mode}" "${DOCS_FILE_PATTERN}"
      if skip_when_no_files; then
        return 0
      fi

      python linting/banned/terms.py "${FILES[@]}"
      codespell --ignore-words .codespellignore "${FILES[@]}"

      collect_mode_files "${mode}" "${MARKDOWN_FILE_PATTERN}"
      if [[ ${#FILES[@]} -gt 0 ]]; then
        python linting/pymarkdown/run.py scan "${FILES[@]}"
      fi
      ;;
    lint:push)
      bash scripts/docs.sh
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
    security:push)
      return 0
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
      collect_mode_files "${mode}" "${PYTHON_FILE_PATTERN}"
      if skip_when_no_files; then
        return 0
      fi

      python -m isort --settings-path pyproject.toml --check-only --diff "${FILES[@]}"
      python -m ruff format --config pyproject.toml --check "${FILES[@]}"
      python -m ruff check --config pyproject.toml "${FILES[@]}"
      python linting/naming/no_generic_names.py
      python linting/runtime/no_print_statements.py
      python linting/runtime/no_shell_true_subprocess.py
      python linting/infra/version_pins.py
      python linting/infra/config_integrity.py
      ;;
    python:push)
      bash scripts/lint.sh --only code
      ;;
    shell:commit)
      collect_mode_files "${mode}" "${SHELL_FILE_PATTERN}"
      if skip_when_no_files; then
        return 0
      fi

      shellcheck -x -e SC1091 "${FILES[@]}"
      shfmt -d -i 2 -ci -s "${FILES[@]}"
      python linting/runtime/no_inline_python.py
      python linting/shell/run.py "${FILES[@]}"
      ;;
    shell:push)
      bash scripts/lint.sh --only shell
      ;;
    docs:commit)
      run_global_stage lint --mode=commit
      ;;
    docs:push)
      bash scripts/docs.sh
      ;;
    docker:commit)
      local saw_docker_input=0
      collect_mode_files "${mode}" "${DOCKERFILE_PATTERN}"
      if [[ ${#FILES[@]} -gt 0 ]]; then
        saw_docker_input=1
        for dockerfile in "${FILES[@]}"; do
          hadolint --failure-threshold error "${dockerfile}"
        done
      fi

      collect_mode_files "${mode}" "${DOCKER_POLICY_PATTERN}"
      if [[ ${#FILES[@]} -gt 0 ]]; then
        python linting/infra/dockerignore_policy.py
        return 0
      fi

      if [[ ${saw_docker_input} == "0" ]]; then
        echo "skip"
      fi
      ;;
    docker:push)
      bash scripts/lint.sh --only docker
      ;;
    quality:commit | security:commit | tests:commit)
      echo "skip"
      ;;
    quality:push)
      bash scripts/lint.sh --only quality
      ;;
    security:push)
      bash scripts/security.sh
      ;;
    tests:push)
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
