#!/usr/bin/env bash

# Environment defaults and dependency installation for scripts/restart.sh
# Requires: SCRIPT_DIR, ROOT_DIR, INSTALL_DEPS

restart_apply_defaults_and_deps() {
  log_info "[restart] Loading environment defaults..."
  source "${SCRIPT_DIR}/steps/04_env_defaults.sh"

  if [ "${INSTALL_DEPS}" = "1" ]; then
    log_info "[restart] Reinstalling all dependencies from scratch (--install-deps)"
    
    # Wipe all existing pip dependencies and caches for clean install
    # Preserves models, HF cache, TRT repo
    wipe_dependencies_for_reinstall
    
    # Ensure correct Python version is available (TRT needs 3.10, vLLM uses system python)
    # Explicitly pass INFERENCE_ENGINE to subprocess
    INFERENCE_ENGINE="${INFERENCE_ENGINE:-trt}" "${SCRIPT_DIR}/steps/02_python_env.sh" || {
      log_err "[restart] Failed to set up Python environment"
      exit 1
    }
    
    # Reinstall all dependencies from scratch (force mode)
    FORCE_REINSTALL=1 INFERENCE_ENGINE="${INFERENCE_ENGINE:-trt}" "${SCRIPT_DIR}/steps/03_install_deps.sh"
  else
    log_info "[restart] Skipping dependency installation (default)"
  fi
}


