#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/utils.sh"

log_info "Wiping runtime deps and caches; keeping repo and container services alive"

# 1) Stop our uvicorn server if running (leave Jupyter/other services alone)
if pgrep -f "uvicorn src.server:app" >/dev/null 2>&1; then
  log_info "Stopping uvicorn (src.server:app)"
  pkill -f "uvicorn src.server:app" || true
  sleep 1
  # Force kill if still present
  if pgrep -f "uvicorn src.server:app" >/dev/null 2>&1; then
    pkill -9 -f "uvicorn src.server:app" || true
  fi
else
  log_info "No uvicorn server process found"
fi

# 2) Uninstall Python packages we installed (from requirements.txt)
if [ -f "${ROOT_DIR}/requirements.txt" ]; then
  log_info "Uninstalling pip packages listed in requirements.txt"
  python -m pip uninstall -y -r "${ROOT_DIR}/requirements.txt" || true
else
  log_warn "requirements.txt not found; skipping pip uninstall step"
fi

# 3) Remove virtual environments commonly used
for VENV_DIR in \
  "${ROOT_DIR}/.venv" \
  "${ROOT_DIR}/venv" \
  "${ROOT_DIR}/env" \
  "${ROOT_DIR}/.env"
do
  if [ -d "$VENV_DIR" ]; then
    log_info "Removing virtual environment at $VENV_DIR"
    rm -rf "$VENV_DIR" || true
  fi
done

# 4) Clear LMCache local store (disk) — repo-local
if [ -d "${ROOT_DIR}/.lmcache_store" ]; then
  log_info "Clearing LMCache disk store at ${ROOT_DIR}/.lmcache_store"
  rm -rf "${ROOT_DIR}/.lmcache_store"/* || true
fi

# 5) Clear HuggingFace model caches (models will re-download next run)
for HF_DIR in \
  "$HOME/.cache/huggingface" \
  "/root/.cache/huggingface"
do
  if [ -d "$HF_DIR" ]; then
    log_info "Removing HuggingFace cache at $HF_DIR"
    rm -rf "$HF_DIR" || true
  fi
done

# 6) Clear pip cache
log_info "Purging pip cache"
python -m pip cache purge || true
for PIP_CACHE in "$HOME/.cache/pip" "/root/.cache/pip"; do
  [ -d "$PIP_CACHE" ] && rm -rf "$PIP_CACHE" || true
done

# 7) Clear Torch cache
for TORCH_CACHE in "$HOME/.cache/torch" "/root/.cache/torch"; do
  if [ -d "$TORCH_CACHE" ]; then
    log_info "Removing torch cache at $TORCH_CACHE"
    rm -rf "$TORCH_CACHE" || true
  fi
done

# 8) Clear NVIDIA PTX JIT cache (GPU kernel cache)
for NV_CACHE in "$HOME/.nv/ComputeCache" "/root/.nv/ComputeCache"; do
  if [ -d "$NV_CACHE" ]; then
    log_info "Removing NVIDIA ComputeCache at $NV_CACHE"
    rm -rf "$NV_CACHE" || true
  fi
done

# 9) Clear project __pycache__ and pytest caches
log_info "Removing __pycache__ and .pytest_cache in repo"
find "${ROOT_DIR}" -type d -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true
find "${ROOT_DIR}" -type d -name ".pytest_cache" -prune -exec rm -rf {} + 2>/dev/null || true

# 10) Legacy cleanup for old /workspace LMCache paths
if [ -f "/workspace/lmcache.yaml" ]; then
  log_info "Removing legacy /workspace/lmcache.yaml"
  rm -f /workspace/lmcache.yaml || true
fi
if [ -d "/workspace/lmcache_store" ]; then
  log_info "Removing legacy /workspace/lmcache_store"
  rm -rf /workspace/lmcache_store || true
fi

log_info "Done. Repo preserved. Jupyter/console/container remain running."


