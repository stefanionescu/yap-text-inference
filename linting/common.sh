#!/usr/bin/env bash
# Shared linting helpers for repo-local Python tool resolution.

set -euo pipefail

LINTING_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
REPO_VENV_DIR="${LINTING_ROOT}/.venv"
REPO_PYTHON_BIN="${REPO_VENV_DIR}/bin/python"
REPO_JS_BIN_DIR="${LINTING_ROOT}/node_modules/.bin"
REPO_TOOL_CACHE_DIR="${LINTING_ROOT}/.cache/tooling"
REPO_TOOL_BIN_DIR="${REPO_TOOL_CACHE_DIR}/bin"
REPO_BUN_BIN_DIR="${HOME:-}/.bun/bin"

# ensure_repo_python_env - Prefer the repo-managed Python toolchain for linting and security commands.
ensure_repo_python_env() {
  if [[ ! -x ${REPO_PYTHON_BIN} ]]; then
    echo "error: repo Python environment missing at ${REPO_PYTHON_BIN}" >&2
    echo "error: create ${REPO_VENV_DIR} and install requirements-dev.txt before running lint/security checks" >&2
    exit 1
  fi

  export REPO_PYTHON="${REPO_PYTHON_BIN}"
  export PATH="${REPO_VENV_DIR}/bin:${REPO_JS_BIN_DIR}:${REPO_TOOL_BIN_DIR}:${REPO_BUN_BIN_DIR}:${PATH}"
  hash -r
}
