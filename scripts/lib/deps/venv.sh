#!/usr/bin/env bash

# Virtual environment helpers

ensure_virtualenv() {
  local venv_path="${ROOT_DIR}/.venv"
  local venv_python="${venv_path}/bin/python"

  if [ -d "${venv_path}" ] && [ ! -x "${venv_python}" ]; then
    log_warn "[venv] Existing virtualenv missing python binary; recreating ${venv_path}"
    rm -rf "${venv_path}"
  fi

  if [ ! -d "${venv_path}" ]; then
    log_info "[venv] Creating virtual environment at ${venv_path}"
    PY_BIN="python3"
    if ! command -v ${PY_BIN} >/dev/null 2>&1; then
      PY_BIN="python"
    fi

    if ! ${PY_BIN} -m venv "${venv_path}" >/dev/null 2>&1; then
      log_warn "[venv] python venv failed (ensurepip missing?). Trying virtualenv."
      if ! ${PY_BIN} -m pip --version >/dev/null 2>&1; then
        log_warn "[venv] pip is not available; attempting to bootstrap pip."
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
        log_warn "[venv] Failed to upgrade pip; continuing."
      fi
      if ! ${PY_BIN} -m pip install virtualenv >/dev/null 2>&1; then
        log_warn "[venv] virtualenv install failed via pip. Attempting OS package for venv."
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
        log_info "[venv] Creating venv with virtualenv"
        if ${PY_BIN} -m virtualenv --version >/dev/null 2>&1; then
          ${PY_BIN} -m virtualenv "${venv_path}"
        else
          virtualenv -p "${PY_BIN}" "${venv_path}"
        fi
      else
        log_err "[venv] Failed to create a virtual environment. Install python3-venv or virtualenv and retry."
        return 1
      fi
    fi
  fi
}

ensure_pip_in_venv() {
  local venv_python="${ROOT_DIR}/.venv/bin/python"

  if [ ! -x "${venv_python}" ]; then
    log_err "[venv] Virtual environment missing python binary; run ensure_virtualenv first."
    return 1
  fi

  if ! "${venv_python}" -m pip --version >/dev/null 2>&1; then
    log_warn "[venv] pip missing in virtual environment; bootstrapping pip."
    if ! "${venv_python}" -m ensurepip --upgrade >/dev/null 2>&1; then
      TMP_PIP="${ROOT_DIR}/.get-pip.py"
      if command -v curl >/dev/null 2>&1; then
        curl -fsSL -o "${TMP_PIP}" https://bootstrap.pypa.io/get-pip.py || true
      elif command -v wget >/dev/null 2>&1; then
        wget -qO "${TMP_PIP}" https://bootstrap.pypa.io/get-pip.py || true
      fi
      if [ -f "${TMP_PIP}" ]; then
        "${venv_python}" "${TMP_PIP}" || true
        rm -f "${TMP_PIP}" || true
      fi
    fi
  fi

  if "${venv_python}" -m pip --version >/dev/null 2>&1; then
    "${venv_python}" -m pip install --upgrade pip
  else
    log_err "[venv] pip is not available in the virtual environment; please install python3-venv or virtualenv and retry."
    return 1
  fi
}


