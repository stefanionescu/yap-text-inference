#!/usr/bin/env bash
# run_lint - Main lint entrypoint for code, shell, docs, docker, quality, and hooks.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
RUN_FIX=0
RUN_FAST=0
ONLY=""

# usage - Print CLI usage.
usage() {
  cat <<'USAGE'
Usage: linting/lint.sh [--fix] [--fast] [--only code|shell|docs|docker|quality|hooks]

Runs repository lint stages:
  - code:    ruff, isort, mypy, import-linter, custom Python lint rules
  - shell:   shellcheck, shfmt, custom shell lint rules, inline-python guard
  - docs:    pymarkdown, prose rules, codespell, banned-term scan
  - docker:  hadolint and dockerignore policy
  - quality: lizard, deptry, vulture, jscpd
  - hooks:   self-check .githooks

Options:
  --fix      Apply formatter fixes where available
  --fast     Skip docs/docker/quality stages
  --only     Run a single stage
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --fix)
      RUN_FIX=1
      shift
      ;;
    --fast)
      RUN_FAST=1
      shift
      ;;
    --only)
      ONLY="${2:-}"
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

# run_cmd - Run a command and show its buffered output on failure.
run_cmd() {
  local label="$1"
  shift
  local tmp
  tmp="$(mktemp)"
  if "$@" >"${tmp}" 2>&1; then
    rm -f "${tmp}"
    return 0
  fi
  echo "[lint] ${label} failed" >&2
  cat "${tmp}" >&2
  rm -f "${tmp}"
  return 1
}

# run_code_full - Run full-repo Python code linting and custom structural rules.
run_code_full() {
  cd "${ROOT_DIR}"

  if [[ ${RUN_FIX} -eq 1 ]]; then
    run_cmd "isort" python -m isort --settings-path pyproject.toml "${ROOT_DIR}"
    run_cmd "ruff format" python -m ruff format --config pyproject.toml "${ROOT_DIR}"
    run_cmd "ruff check" python -m ruff check --config pyproject.toml --fix "${ROOT_DIR}"
  else
    run_cmd "isort" python -m isort --settings-path pyproject.toml --check-only --diff "${ROOT_DIR}"
    run_cmd "ruff format" python -m ruff format --config pyproject.toml --check "${ROOT_DIR}"
    run_cmd "ruff check" python -m ruff check --config pyproject.toml "${ROOT_DIR}"
  fi

  run_cmd "import-linter" lint-imports
  run_cmd "mypy" python -m mypy --follow-imports=skip src tests
  run_cmd "import-cycles" python linting/imports/import_cycles.py
  run_cmd "single-line-imports-first" python linting/imports/single_line_imports_first.py
  run_cmd "all-at-bottom" python linting/structure/all_at_bottom.py
  run_cmd "file-length" python linting/structure/file_length.py
  run_cmd "function-length" python linting/structure/function_length.py
  run_cmd "one-class-per-file" python linting/structure/one_class_per_file.py
  run_cmd "single-file-folders" python linting/structure/single_file_folders.py
  run_cmd "prefix-collisions" python linting/structure/prefix_collisions.py
  run_cmd "function-order" python linting/structure/function_order.py
  run_cmd "no-runtime-singletons" python linting/runtime/no_runtime_singletons.py
  run_cmd "no-lazy-module-loading" python linting/imports/no_lazy_module_loading.py
  run_cmd "no-legacy-markers" python linting/runtime/no_legacy_markers.py
  run_cmd "no-config-functions" python linting/modules/no_config_functions.py
  run_cmd "no-config-cross-imports" python linting/modules/no_config_cross_imports.py
  run_cmd "test-file-prefix" python linting/testing/file_prefix.py
  run_cmd "test-function-placement" python linting/testing/function_placement.py
  run_cmd "unit-test-domain-folders" python linting/testing/unit_test_domain_folders.py
  run_cmd "no-conftest-in-subfolders" python linting/testing/no_conftest_in_subfolders.py
  run_cmd "generic-names" python linting/naming/no_generic_names.py
  run_cmd "no-print-statements" python linting/runtime/no_print_statements.py
  run_cmd "no-shell-true-subprocess" python linting/runtime/no_shell_true_subprocess.py
  run_cmd "version-pins" python linting/infra/version_pins.py
  run_cmd "config-integrity" python linting/infra/config_integrity.py
}

# run_code - Run Python code linting and custom structural rules.
run_code() {
  run_code_full
}

# collect_shell_files - Populate the shared SHELL_FILES array for full-repo shell linting.
collect_shell_files() {
  SHELL_FILES=()
  while IFS= read -r -d '' file; do
    SHELL_FILES+=("${file}")
  done < <(find scripts docker linting -type f \( -name "*.sh" -o -name "pre-commit" -o -name "pre-push" -o -name "commit-msg" \) -print0)
}

# run_shell_full - Run full-repo shell linting and custom shell rules.
run_shell_full() {
  cd "${ROOT_DIR}"
  collect_shell_files

  if [[ ${#SHELL_FILES[@]} -eq 0 ]]; then
    return 0
  fi

  run_cmd "shellcheck" shellcheck -x -e SC1091 "${SHELL_FILES[@]}"
  if [[ ${RUN_FIX} -eq 1 ]]; then
    run_cmd "shfmt" shfmt -w -i 2 -ci -s "${SHELL_FILES[@]}"
  else
    run_cmd "shfmt" shfmt -d -i 2 -ci -s "${SHELL_FILES[@]}"
  fi
  run_cmd "no-inline-python" python linting/runtime/no_inline_python.py
  run_cmd "shell-custom-rules" python linting/shell/run.py
}

# run_shell - Run shell linting and custom shell rules.
run_shell() {
  run_shell_full
}

# run_docs - Run documentation-oriented lint checks.
run_docs() {
  bash "${ROOT_DIR}/linting/docs/run.sh"
}

# run_docker_full - Run full-repo Docker-specific lint checks.
run_docker_full() {
  cd "${ROOT_DIR}"
  while IFS= read -r dockerfile; do
    run_cmd "hadolint ${dockerfile}" hadolint --failure-threshold error "${dockerfile}"
  done < <(find docker -name Dockerfile | sort)
  run_cmd "dockerignore-policy" python linting/infra/dockerignore_policy.py
}

# run_docker - Run Docker-specific lint checks.
run_docker() {
  run_docker_full
}

# run_quality - Run structural and maintenance quality checks.
run_quality() {
  cd "${ROOT_DIR}"
  run_cmd "lizard" bash linting/lizard/run.sh
  run_cmd "deptry" python -m deptry --config pyproject.toml src tests
  run_cmd "vulture" python -m vulture src linting --min-confidence 100
  run_cmd "jscpd python" bunx jscpd --config .jscpd/python.json
  run_cmd "jscpd bash" bunx jscpd --config .jscpd/bash.json
}

# run_hooks - Run self-linting on the hook tree if it exists.
run_hooks() {
  local hooks_dir="${ROOT_DIR}/.githooks/hooks/self"
  if [[ ! -d ${hooks_dir} ]]; then
    return 0
  fi
  bash "${hooks_dir}/lint.sh"
  bash "${hooks_dir}/security.sh"
  bash "${hooks_dir}/format.sh"
  bash "${hooks_dir}/quality.sh"
}

case "${ONLY}" in
  code)
    run_code
    ;;
  shell)
    run_shell
    ;;
  docs)
    run_docs
    ;;
  docker)
    run_docker
    ;;
  quality)
    run_quality
    ;;
  hooks)
    run_hooks
    ;;
  "")
    run_code
    run_shell
    if [[ ${RUN_FAST} -eq 0 ]]; then
      run_docs
      run_docker
      run_quality
      run_hooks
    fi
    ;;
  *)
    echo "Unknown --only value: ${ONLY}" >&2
    exit 2
    ;;
esac
