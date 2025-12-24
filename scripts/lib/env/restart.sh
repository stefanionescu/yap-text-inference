#!/usr/bin/env bash

# Environment defaults and dependency installation for scripts/restart.sh
# Requires: SCRIPT_DIR, ROOT_DIR, INSTALL_DEPS
# Note: restart_run_install_deps_if_needed is defined in restart/basic.sh

# Source fla.sh for model-specific dependency handling
LIB_DIR="${SCRIPT_DIR}/lib"
source "${LIB_DIR}/deps/fla.sh"

restart_apply_defaults_and_deps() {
  # Handle --install-deps (uses shared helper from basic.sh)
  restart_run_install_deps_if_needed

  # Load environment defaults (after deps are installed)
  log_info "[restart] Loading environment defaults..."
  source "${SCRIPT_DIR}/steps/04_env_defaults.sh"
  
  # Model-specific dependencies (e.g., fla-core for Kimi models)
  # Only run if venv exists and is active
  if [ -d "${ROOT_DIR}/.venv" ]; then
    ensure_fla_core_if_needed || log_warn "[restart] fla-core installation failed, continuing..."
  fi
}


