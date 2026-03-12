#!/usr/bin/env bash
# Shared repo bootstrap for linting and hook shell entrypoints.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
REPO_VENV_DIR="${REPO_ROOT}/.venv"
REPO_PYTHON_BIN="${REPO_VENV_DIR}/bin/python"
REPO_JS_BIN_DIR="${REPO_ROOT}/node_modules/.bin"
REPO_TOOL_CACHE_DIR="${REPO_ROOT}/.cache/tooling"
REPO_TOOL_BIN_DIR="${REPO_TOOL_CACHE_DIR}/bin"
REPO_BUN_BIN_DIR="${HOME:-}/.bun/bin"

# prepend_repo_path - Add a directory to PATH once, preserving existing precedence.
prepend_repo_path() {
  local dir="$1"
  [[ -n ${dir} ]] || return 0
  case ":${PATH}:" in
    *":${dir}:"*) ;;
    *) export PATH="${dir}:${PATH}" ;;
  esac
}

# activate_repo_tool_paths - Add the repo-managed tool locations to PATH without requiring the Python venv.
activate_repo_tool_paths() {
  prepend_repo_path "${REPO_BUN_BIN_DIR}"
  prepend_repo_path "${REPO_TOOL_BIN_DIR}"
  prepend_repo_path "${REPO_JS_BIN_DIR}"
  if [[ -d ${REPO_VENV_DIR}/bin ]]; then
    prepend_repo_path "${REPO_VENV_DIR}/bin"
  fi
  if [[ -x ${REPO_PYTHON_BIN} ]]; then
    export REPO_PYTHON="${REPO_PYTHON_BIN}"
  fi
  hash -r
}

# ensure_repo_python_env - Prefer the repo-managed Python toolchain for linting and security commands.
ensure_repo_python_env() {
  if [[ ! -x ${REPO_PYTHON_BIN} ]]; then
    echo "error: repo Python environment missing at ${REPO_PYTHON_BIN}" >&2
    echo "error: create ${REPO_VENV_DIR} and install requirements-dev.txt before running lint/security checks" >&2
    exit 1
  fi

  export REPO_PYTHON="${REPO_PYTHON_BIN}"
  activate_repo_tool_paths
}
