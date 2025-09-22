#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/utils.sh"

log_info "Installing Python dependencies"

export PIP_ROOT_USER_ACTION=${PIP_ROOT_USER_ACTION:-ignore}
export PIP_DISABLE_PIP_VERSION_CHECK=${PIP_DISABLE_PIP_VERSION_CHECK:-1}
export PIP_NO_INPUT=${PIP_NO_INPUT:-1}
export PIP_PREFER_BINARY=${PIP_PREFER_BINARY:-1}

if [ ! -d "${ROOT_DIR}/.venv" ]; then
  log_info "Creating virtual environment at ${ROOT_DIR}/.venv"
  python -m venv "${ROOT_DIR}/.venv"
fi

"${ROOT_DIR}/.venv/bin/python" -m pip install --upgrade pip

# Skip reinstall if requirements.txt didn't change since last successful install
REQ_FILE="${ROOT_DIR}/requirements.txt"
STAMP_FILE="${ROOT_DIR}/.venv/.req_hash"
if [ -f "${STAMP_FILE}" ] && [ -f "${REQ_FILE}" ]; then
  CUR_HASH=$(sha256sum "${REQ_FILE}" | awk '{print $1}')
  OLD_HASH=$(cat "${STAMP_FILE}" 2>/dev/null || true)
  if [ "${CUR_HASH}" = "${OLD_HASH}" ]; then
    log_info "Dependencies unchanged; skipping pip install"
    exit 0
  fi
fi

"${ROOT_DIR}/.venv/bin/pip" install --upgrade-strategy only-if-needed -r "${ROOT_DIR}/requirements.txt"

# Record the hash after a successful install
if [ -f "${REQ_FILE}" ]; then
  sha256sum "${REQ_FILE}" | awk '{print $1}' > "${STAMP_FILE}" || true
fi


