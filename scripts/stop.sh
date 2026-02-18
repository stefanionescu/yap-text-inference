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
source "${SCRIPT_DIR}/config/values/core.sh"
source "${SCRIPT_DIR}/config/messages/stop.sh"
source "${SCRIPT_DIR}/lib/runtime/cleanup/main.sh"
source "${SCRIPT_DIR}/lib/env/stop.sh"

stop_init_flags

# =============================================================================
# CLEANUP CONTROL FLAGS
# =============================================================================
# FULL_CLEANUP=0: Light stop - preserve venv, caches, models (for quick restart)
# FULL_CLEANUP=1: Full stop - wipe EVERYTHING: venv, caches, models, all of it
# =============================================================================
if [ "${FULL_CLEANUP}" = "0" ]; then
  log_info "${CFG_STOP_MSG_LIGHT_STOP}"
else
  log_info "${CFG_STOP_MSG_FULL_STOP}"
fi

log_info "${CFG_STOP_MSG_STOPPING_SERVER}"
cleanup_stop_server_session "${ROOT_DIR}"
log_info "${CFG_STOP_MSG_KILLING_HELPERS}"
cleanup_kill_engine_processes
sleep 1

# 4) Remove repo-local caches (models and compiled artifacts under the repo)
if [ "${FULL_CLEANUP}" != "0" ]; then
  log_info "${CFG_STOP_MSG_DELETE_REPO_CACHES}"
  cleanup_repo_caches "${ROOT_DIR}"
  log_info "${CFG_STOP_MSG_REMOVE_VENVS}"
  cleanup_venvs "${ROOT_DIR}"
fi

log_infof "${CFG_STOP_MSG_CLEAN_GPU}" "${HARD_RESET}"
cleanup_gpu_processes "${HARD_RESET}"

if [ "${FULL_CLEANUP}" != "0" ]; then
  log_info "${CFG_STOP_MSG_DELETE_HF}"
  cleanup_hf_caches
fi

log_info "${CFG_STOP_MSG_DELETE_MISC}"
cleanup_misc_caches

if [ "${FULL_CLEANUP}" != "0" ]; then
  log_info "${CFG_STOP_MSG_PURGE_PIP}"
  cleanup_pip_caches
fi

log_info "${CFG_STOP_MSG_REMOVE_ARTIFACTS}"
cleanup_python_artifacts "${ROOT_DIR}"
log_info "${CFG_STOP_MSG_CLEAR_TMP}"
cleanup_tmp_dirs

if [ "${FULL_CLEANUP}" != "0" ]; then
  log_info "${CFG_STOP_MSG_REMOVE_RUNTIME_STATE}"
  cleanup_runtime_state "${ROOT_DIR}"
  log_info "${CFG_STOP_MSG_DELETE_HOME_CACHE}"
  cleanup_home_cache_roots
fi

log_info "${CFG_STOP_MSG_REMOVE_SERVER_ARTIFACTS}"
cleanup_server_artifacts "${ROOT_DIR}"

if [ "${FULL_CLEANUP}" = "0" ]; then
  log_info "${CFG_STOP_MSG_DONE_LIGHT}"
else
  log_info "${CFG_STOP_MSG_DONE_FULL}"
fi
