#!/usr/bin/env bash
# shellcheck disable=SC1091
# =============================================================================
# Server Stop Script
# =============================================================================
# Stops the inference server and performs cleanup operations.
# Supports light stop (preserving venv/caches) or full cleanup.
#
# Usage: FULL_CLEANUP=0|1 bash scripts/stop.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/lib/noise/python.sh"
source "${SCRIPT_DIR}/lib/common/log.sh"
source "${SCRIPT_DIR}/lib/runtime/cleanup.sh"
source "${SCRIPT_DIR}/lib/env/stop.sh"

stop_init_flags

# =============================================================================
# CLEANUP CONTROL FLAGS
# =============================================================================
# FULL_CLEANUP=0: Light stop - preserve venv, caches, models (for quick restart)
# FULL_CLEANUP=1: Full stop - wipe EVERYTHING: venv, caches, models, all of it
# =============================================================================
if [ "${FULL_CLEANUP}" = "0" ]; then
  log_info "[stop] Light stop: preserving venv, caches, and models..."
else
  log_info "[stop] Full stop: wiping venv, caches, models..."
fi

log_info "[stop] Stopping uvicorn server session and clearing server.pid..."
cleanup_stop_server_session "${ROOT_DIR}"
log_info "[stop] Killing lingering engine helper processes..."
cleanup_kill_engine_processes
sleep 1

# 4) Remove repo-local caches (models and compiled artifacts under the repo)
if [ "${FULL_CLEANUP}" != "0" ]; then
  log_info "[stop] Deleting repo caches, compiled artifacts, and checked-out models..."
  cleanup_repo_caches "${ROOT_DIR}"
  log_info "[stop] Removing Python virtual environments..."
  cleanup_venvs "${ROOT_DIR}"
fi

log_info "[stop] Cleaning GPU processes (hard reset=${HARD_RESET})..."
cleanup_gpu_processes "${HARD_RESET}"

if [ "${FULL_CLEANUP}" != "0" ]; then
  log_info "[stop] Deleting Hugging Face caches and configs..."
  cleanup_hf_caches
fi

log_info "[stop] Deleting system/compiler runtime caches..."
cleanup_misc_caches

if [ "${FULL_CLEANUP}" != "0" ]; then
  log_info "[stop] Purging pip caches..."
  cleanup_pip_caches
fi

log_info "[stop] Removing Python build/test artifacts..."
cleanup_python_artifacts "${ROOT_DIR}"
log_info "[stop] Clearing /tmp and /dev/shm scratch directories..."
cleanup_tmp_dirs

if [ "${FULL_CLEANUP}" != "0" ]; then
  log_info "[stop] Removing runtime state tracking..."
  cleanup_runtime_state "${ROOT_DIR}"
  log_info "[stop] Deleting home cache roots..."
  cleanup_home_cache_roots
fi

log_info "[stop] Removing server log artifacts..."
cleanup_server_artifacts "${ROOT_DIR}"

if [ "${FULL_CLEANUP}" = "0" ]; then
  log_info "[stop] Done. Repo preserved. Jupyter/console/container remain running."
else
  log_info "[stop] Done. Full cleanup complete. Restart to resume work."
fi
