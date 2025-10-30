#!/usr/bin/env bash

# Virtual environment helpers

ensure_virtualenv() {
  if [ ! -d "${ROOT_DIR}/.venv" ]; then
    log_info "Creating virtual environment at ${ROOT_DIR}/.venv"
    PY_BIN="python3"
    if ! command -v ${PY_BIN} >/dev/null 2>&1; then
      PY_BIN="python"
    fi

    if ! ${PY_BIN} -m venv "${ROOT_DIR}/.venv" >/dev/null 2>&1; then
      log_warn "python venv failed (ensurepip missing?). Trying virtualenv."
      if ! ${PY_BIN} -m pip --version >/dev/null 2>&1; then
        log_warn "pip is not available; attempting to bootstrap pip."
        TMP_PIP="${ROOT_DIR}/.get-pip.py"
        if command -v curl >/dev/null 2>&1; then
          curl -fsSL -o "${TMP_PIP}" https://bootstrap.pypa.io/get-pip.py || true
        elif command -v wget >/dev/null 2>&1; then
          wget -qO "${TMP_PIP}" https://bootstrap.pypa.io/get-pip.py || true
        fi
        if [ -f "${TMP_PIP}" ]; then
          ${PY_BIN} "${TMP_PIP}" || true
          rm -f "${TMP_PIP}" || true
        fi
      fi

      if ! ${PY_BIN} -m pip install --upgrade pip >/dev/null 2>&1; then
        log_warn "Failed to upgrade pip; continuing."
      fi
      if ! ${PY_BIN} -m pip install virtualenv >/dev/null 2>&1; then
        log_warn "virtualenv install failed via pip. Attempting OS package for venv."
        if command -v apt-get >/dev/null 2>&1; then
          sudo -n apt-get update >/dev/null 2>&1 || true
          sudo -n apt-get install -y python3-venv >/dev/null 2>&1 || true
        elif command -v apk >/dev/null 2>&1; then
          sudo -n apk add --no-cache python3 py3-virtualenv >/dev/null 2>&1 || true
        elif command -v dnf >/dev/null 2>&1; then
          sudo -n dnf install -y python3-venv >/dev/null 2>&1 || true
        elif command -v yum >/dev/null 2>&1; then
          sudo -n yum install -y python3-venv >/dev/null 2>&1 || true
        fi
      fi

      if command -v virtualenv >/dev/null 2>&1 || ${PY_BIN} -m virtualenv --version >/dev/null 2>&1; then
        log_info "Creating venv with virtualenv"
        if ${PY_BIN} -m virtualenv --version >/dev/null 2>&1; then
          ${PY_BIN} -m virtualenv "${ROOT_DIR}/.venv"
        else
          virtualenv -p "${PY_BIN}" "${ROOT_DIR}/.venv"
        fi
      else
        log_err "Failed to create a virtual environment. Install python3-venv or virtualenv and retry."
        return 1
      fi
    fi
  fi
}

ensure_pip_in_venv() {
  if ! "${ROOT_DIR}/.venv/bin/python" -m pip --version >/dev/null 2>&1; then
    log_warn "pip missing in virtual environment; bootstrapping pip."
    if ! "${ROOT_DIR}/.venv/bin/python" -m ensurepip --upgrade >/dev/null 2>&1; then
      TMP_PIP="${ROOT_DIR}/.get-pip.py"
      if command -v curl >/dev/null 2>&1; then
        curl -fsSL -o "${TMP_PIP}" https://bootstrap.pypa.io/get-pip.py || true
      elif command -v wget >/dev/null 2>&1; then
        wget -qO "${TMP_PIP}" https://bootstrap.pypa.io/get-pip.py || true
      fi
      if [ -f "${TMP_PIP}" ]; then
        "${ROOT_DIR}/.venv/bin/python" "${TMP_PIP}" || true
        rm -f "${TMP_PIP}" || true
      fi
    fi
  fi

  if "${ROOT_DIR}/.venv/bin/python" -m pip --version >/dev/null 2>&1; then
    "${ROOT_DIR}/.venv/bin/python" -m pip install --upgrade pip
  else
    log_err "pip is not available in the virtual environment; please install python3-venv or virtualenv and retry."
    return 1
  fi
}


