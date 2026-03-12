#!/usr/bin/env bash
# Set up the repo-local development toolchain used by linting, hooks, and security checks.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"
VENV_PYTHON="${VENV_DIR}/bin/python"
REQUIREMENTS_FILE="${ROOT_DIR}/requirements-dev.txt"

die() {
  echo "error: $1" >&2
  exit 1
}

require_command() {
  local command_name="$1"
  local help_text="$2"
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    die "${command_name} is required to bootstrap repo tooling (${help_text})"
  fi
}

run_step() {
  local label="$1"
  shift
  echo "==> ${label}"
  "$@"
}

ensure_prerequisites() {
  require_command "python3" "install Python 3.10+ first"
  require_command "bun" "install Bun 1.2.7+ first"
  require_command "curl" "required for repo-local tool downloads"
  require_command "tar" "required for repo-local tool downloads"
  require_command "unzip" "required for repo-local CodeQL downloads"
}

ensure_repo_venv() {
  if [[ ! -x ${VENV_PYTHON} ]]; then
    run_step "creating ${VENV_DIR}" python3 -m venv "${VENV_DIR}"
  fi

  if ! "${VENV_PYTHON}" -m pip --version >/dev/null 2>&1; then
    run_step "bootstrapping pip in ${VENV_DIR}" "${VENV_PYTHON}" -m ensurepip --upgrade
  fi
}

install_python_dev_tools() {
  if [[ ! -f ${REQUIREMENTS_FILE} ]]; then
    die "missing ${REQUIREMENTS_FILE}"
  fi

  run_step "installing Python dev tooling" \
    "${VENV_PYTHON}" -m pip install --disable-pip-version-check -r "${REQUIREMENTS_FILE}"
}

install_bun_dev_tools() {
  cd "${ROOT_DIR}"
  run_step "installing Bun dev tooling" bun install
}

install_repo_local_tools() {
  cd "${ROOT_DIR}"
  run_step "installing repo-local linting CLIs" bash linting/tooling/install.sh all
  run_step "installing repo-local security CLIs" bash linting/security/install.sh all
}

show_summary() {
  cat <<'SUMMARY'

Repo tooling is ready.

Next steps:
  bash .githooks/lib/setup.sh
  nox -s lint
  nox -s test
  nox -s security
SUMMARY
}

ensure_prerequisites
ensure_repo_venv
install_python_dev_tools
install_bun_dev_tools
install_repo_local_tools
show_summary
