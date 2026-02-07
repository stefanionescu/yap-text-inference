#!/usr/bin/env bash
# =============================================================================
# Stop Script Defaults
# =============================================================================
# Initializes flags for stop.sh including cleanup mode (light vs full)
# and hard reset behavior.

stop_init_flags() {
  export HARD_RESET="${HARD_RESET:-0}"
  # FULL_CLEANUP controls whether to preserve or wipe caches/venvs during stop
  # 0 = light stop (preserve), 1 = full cleanup (wipe everything)
  export FULL_CLEANUP="${FULL_CLEANUP:-${NUKE_ALL:-1}}"
}
