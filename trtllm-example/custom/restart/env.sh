#!/usr/bin/env bash

# Environment defaults and dependency handling for custom/restart.sh

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
    _log_info "Installing/upgrading dependencies (--install-deps)"
    bash "custom/setup/install-dependencies.sh" || {
      _log_error "Dependency installation failed"
      return 1
    }
  else
    _log_info "Skipping dependency installation (default)"
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
