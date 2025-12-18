#!/usr/bin/env bash

# Environment defaults and dependency installation for scripts/restart.sh
# Requires: SCRIPT_DIR, ROOT_DIR, INSTALL_DEPS

restart_apply_defaults_and_deps() {
  log_info "[restart] Loading environment defaults..."
  source "${SCRIPT_DIR}/steps/04_env_defaults.sh"

  if [ "${INSTALL_DEPS}" = "1" ]; then
    log_info "[restart] Installing dependencies as requested (--install-deps)"
    if [ ! -d "${ROOT_DIR}/.venv" ]; then
      "${SCRIPT_DIR}/steps/02_python_env.sh"
    fi
    "${SCRIPT_DIR}/steps/03_install_deps.sh"
  else
    log_info "[restart] Skipping dependency installation (default)"
  fi
}


