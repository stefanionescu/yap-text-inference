#!/usr/bin/env bash
# =============================================================================
# Stop Script Defaults
# =============================================================================
# Initializes flags for stop.sh including cleanup mode (light vs full)
# and hard reset behavior.

_STOP_ENV_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../config/values/core.sh
source "${_STOP_ENV_DIR}/../../config/values/core.sh"

stop_init_flags() {
  export HARD_RESET="${HARD_RESET:-${CFG_STOP_DEFAULT_HARD_RESET}}"
  # FULL_CLEANUP controls whether to preserve or wipe caches/venvs during stop
  # 0 = light stop (preserve), 1 = full cleanup (wipe everything)
  export FULL_CLEANUP="${FULL_CLEANUP:-${NUKE_ALL:-${CFG_STOP_DEFAULT_FULL_CLEANUP}}}"
}
