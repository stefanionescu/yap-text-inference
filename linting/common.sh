#!/usr/bin/env bash
# Shared linting helpers for repo-local Python tool resolution.

set -euo pipefail

LINTING_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
REPO_VENV_DIR="${LINTING_ROOT}/.venv"
REPO_PYTHON_BIN="${REPO_VENV_DIR}/bin/python"

# ensure_repo_python_env - Prefer the repo-managed Python toolchain for linting and security commands.
ensure_repo_python_env() {
  if [[ ! -x ${REPO_PYTHON_BIN} ]]; then
    echo "error: repo Python environment missing at ${REPO_PYTHON_BIN}" >&2
    echo "error: create ${REPO_VENV_DIR} and install requirements-dev.txt before running lint/security checks" >&2
    exit 1
  fi

  export REPO_PYTHON="${REPO_PYTHON_BIN}"
  export PATH="${REPO_VENV_DIR}/bin:${PATH}"
  hash -r
}
