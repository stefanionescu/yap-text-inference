#!/usr/bin/env bash

# Helper functions for restart configuration state (precision inheritance, etc.)

restart_resolve_precision_mode() {
  # Honor explicit env
  if [[ -n "${ORPHEUS_PRECISION_MODE:-}" ]]; then
    return 0
  fi

  local config_file="${ROOT_DIR:-.}/.run/build_config.env"
  if [[ -f "$config_file" ]]; then
    # shellcheck disable=SC1090
    source "$config_file" 2>/dev/null || true
    if [[ -n "${BUILD_PRECISION_MODE:-}" ]]; then
      ORPHEUS_PRECISION_MODE="$BUILD_PRECISION_MODE"
      if declare -F log_info >/dev/null 2>&1; then
        log_info "Using ORPHEUS_PRECISION_MODE='${ORPHEUS_PRECISION_MODE}' from last build"
      else
        echo "[restart:config] ORPHEUS_PRECISION_MODE='${ORPHEUS_PRECISION_MODE}' (from last build)"
      fi
    fi
  fi
}

