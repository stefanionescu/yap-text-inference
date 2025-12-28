#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/lib/common/log.sh"
source "${SCRIPT_DIR}/lib/runtime/cleanup.sh"

HARD_RESET="${HARD_RESET:-0}" # set HARD_RESET=1 to attempt nvidia-smi --gpu-reset

# =============================================================================
# CLEANUP CONTROL FLAGS
# =============================================================================
# NUKE_ALL=0: Light stop - preserve venv, caches, models (for quick restart)
# NUKE_ALL=1: Full stop - wipe EVERYTHING: venv, caches, models, all of it
# =============================================================================
NUKE_ALL="${NUKE_ALL:-1}"

if [ "${NUKE_ALL}" = "0" ]; then
  log_info "[stop] Light stop: preserving venv, caches, and models..."
else
  log_info "[stop] Full stop: nuking venv, caches, models..."
fi

cleanup_stop_server_session "${ROOT_DIR}"
cleanup_kill_engine_processes
sleep 1

# 4) Remove repo-local caches (models and compiled artifacts under the repo)
if [ "${NUKE_ALL}" != "0" ]; then
  cleanup_repo_caches "${ROOT_DIR}"
  cleanup_venvs "${ROOT_DIR}"
fi

cleanup_gpu_processes "${HARD_RESET}"

if [ "${NUKE_ALL}" != "0" ]; then
  cleanup_hf_caches
fi

cleanup_misc_caches

if [ "${NUKE_ALL}" != "0" ]; then
  cleanup_pip_caches
fi

for TORCH_CACHE in "$HOME/.cache/torch" "/root/.cache/torch"; do
  [ -d "$TORCH_CACHE" ] && rm -rf "$TORCH_CACHE" || true
done

for NV_CACHE in "$HOME/.nv" "/root/.nv"; do
  [ -d "$NV_CACHE" ] && rm -rf "$NV_CACHE" || true
done

cleanup_python_artifacts "${ROOT_DIR}"
cleanup_tmp_dirs

if [ "${NUKE_ALL}" != "0" ]; then
  cleanup_runtime_state "${ROOT_DIR}"
  cleanup_home_cache_roots
fi

cleanup_server_artifacts "${ROOT_DIR}"

log_info "[stop] Done. Repo preserved. Jupyter/console/container remain running."
