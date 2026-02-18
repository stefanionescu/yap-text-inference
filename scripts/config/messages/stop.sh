#!/usr/bin/env bash
# =============================================================================
# Stop Script Message Configuration
# =============================================================================
# Canonical user-facing messages for scripts/stop.sh.

# shellcheck disable=SC2034
readonly CFG_STOP_MSG_LIGHT_STOP="[stop] Light stop: preserving venv, caches, and models..."
readonly CFG_STOP_MSG_FULL_STOP="[stop] Full stop: wiping venv, caches, models..."
readonly CFG_STOP_MSG_STOPPING_SERVER="[stop] Stopping uvicorn server session and clearing server.pid..."
readonly CFG_STOP_MSG_KILLING_HELPERS="[stop] Killing lingering engine helper processes..."
readonly CFG_STOP_MSG_DELETE_REPO_CACHES="[stop] Deleting repo caches, compiled artifacts, and checked-out models..."
readonly CFG_STOP_MSG_REMOVE_VENVS="[stop] Removing Python virtual environments..."
readonly CFG_STOP_MSG_CLEAN_GPU="[stop] Cleaning GPU processes (hard reset=%s)..."
readonly CFG_STOP_MSG_DELETE_HF="[stop] Deleting Hugging Face caches and configs..."
readonly CFG_STOP_MSG_DELETE_MISC="[stop] Deleting system/compiler runtime caches..."
readonly CFG_STOP_MSG_PURGE_PIP="[stop] Purging pip caches..."
readonly CFG_STOP_MSG_REMOVE_ARTIFACTS="[stop] Removing Python build/test artifacts..."
readonly CFG_STOP_MSG_CLEAR_TMP="[stop] Clearing /tmp and /dev/shm scratch directories..."
readonly CFG_STOP_MSG_REMOVE_RUNTIME_STATE="[stop] Removing runtime state tracking..."
readonly CFG_STOP_MSG_DELETE_HOME_CACHE="[stop] Deleting home cache roots..."
readonly CFG_STOP_MSG_REMOVE_SERVER_ARTIFACTS="[stop] Removing server log artifacts..."
readonly CFG_STOP_MSG_DONE_LIGHT="[stop] Done. Repo preserved. Jupyter/console/container remain running."
readonly CFG_STOP_MSG_DONE_FULL="[stop] Done. Full cleanup complete. Restart to resume work."
