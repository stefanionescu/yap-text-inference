#!/usr/bin/env bash

# Environment defaults and dependency handling for scripts/restart.sh

_log_info() { echo "[restart:env] $*"; }
_log_error() { echo "[restart:env] ERROR: $*" 1>&2; }

restart_apply_env_and_deps() {
  # Prefer detected engine if TRTLLM_ENGINE_DIR is unset or invalid
  if [ -z "${TRTLLM_ENGINE_DIR:-}" ] || [ ! -f "${TRTLLM_ENGINE_DIR}/rank0.engine" ]; then
    if [ -n "${DETECTED_ENGINE_DIR:-}" ]; then
      export TRTLLM_ENGINE_DIR="${DETECTED_ENGINE_DIR}"
      _log_info "Exported TRTLLM_ENGINE_DIR='${TRTLLM_ENGINE_DIR}'"
    fi
  fi

  # Optionally (re)install dependencies
  if [ "${INSTALL_DEPS:-0}" = "1" ]; then
    _log_info "Full dependency reinstall requested (--install-deps)"
    _log_info "Nuking existing venv, pip cache, and dep markers..."
    
    # Remove virtual environment entirely for clean slate
    local venv_dir="${VENV_DIR:-$PWD/.venv}"
    if [ -d "$venv_dir" ]; then
      _log_info "Deleting existing venv: $venv_dir"
      rm -rf "$venv_dir"
    fi
    
    # Clear pip cache to force fresh downloads
    _log_info "Clearing pip cache..."
    rm -rf ~/.cache/pip 2>/dev/null || true
    
    # Clear dep markers so build steps reinstall
    rm -f .run/quant_deps_installed 2>/dev/null || true
    
    # Set force flag for both bootstrap and install scripts
    export FORCE_INSTALL_DEPS=1
    
    # Run bootstrap first (system deps)
    _log_info "Running system bootstrap with force install..."
    bash "scripts/setup/bootstrap.sh" || {
      _log_error "System bootstrap failed"
      return 1
    }
    
    # Then run Python dependencies
    _log_info "Running Python dependencies install with force install..."
    bash "scripts/setup/install_dependencies.sh" || {
      _log_error "Dependency installation failed"
      return 1
    }
  else
    _log_info "Skipping dependency installation (using existing deps if available)"
    _log_info "Hint: Use --install-deps to force reinstall all dependencies"
  fi

  # Record last config for future restarts
  mkdir -p .run || true
  cat >.run/last_config.env <<EOF
TRTLLM_ENGINE_DIR="${TRTLLM_ENGINE_DIR:-}"
DETECTED_ENGINE_DIR="${DETECTED_ENGINE_DIR:-}"
DETECTED_QUANTIZATION="${DETECTED_QUANTIZATION:-}"
EOF

  return 0
}
