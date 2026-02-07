#!/usr/bin/env bash
# =============================================================================
# Restart Environment Defaults
# =============================================================================
# Environment defaults and dependency installation for scripts/restart.sh.
# Applies cached configuration and triggers deps install when requested.

apply_defaults_and_deps() {
  # Handle --install-deps (uses shared helper from basic.sh)
  run_install_deps_if_needed

  # Load environment defaults (after deps are installed)
  log_section "[restart] Loading environment defaults..."
  source "${SCRIPT_DIR}/steps/04_env_defaults.sh"
}
