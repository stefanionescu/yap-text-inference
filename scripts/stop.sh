#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/utils.sh"

HARD_RESET="${HARD_RESET:-0}"   # set HARD_RESET=1 to attempt nvidia-smi --gpu-reset
PID_FILE="${ROOT_DIR}/server.pid"

log_info "Wiping runtime deps and caches; keeping repo and container services alive"

# 0) Stop server + ALL its children (vLLM workers) = free VRAM
if [ -f "${PID_FILE}" ]; then
  PID="$(cat "${PID_FILE}")" || true
  if [ -n "${PID:-}" ] && ps -p "${PID}" >/dev/null 2>&1; then
    # uvicorn was started as a session leader via setsid; kill the whole session
    log_info "Stopping server session (PID ${PID})"
    kill -TERM -"${PID}" || true
    # graceful wait up to 10s
    for _ in {1..10}; do
      ps -p "${PID}" >/dev/null 2>&1 || break
      sleep 1
    done
    # hard kill if still alive
    ps -p "${PID}" >/dev/null 2>&1 && kill -KILL -"${PID}" || true
  fi
  rm -f "${PID_FILE}" || true
else
  log_info "No server.pid; best-effort kill by pattern"
  pkill -f "uvicorn src.server:app" || true
fi

# Also kill any orphan vLLM/engine workers just in case
pkill -f "vllm.v1.engine.core" || true
pkill -f "EngineCore_0" || true
pkill -f "python.*vllm" || true

sleep 1

# 1) Verify VRAM is free; if not, kill leftover GPU PIDs
if command -v nvidia-smi >/dev/null 2>&1; then
  log_info "Checking for leftover GPU processes"
  # Get PIDs using the GPU (ignore n/a lines)
  mapfile -t GPIDS < <(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null | awk '{print $1}' | grep -E '^[0-9]+$' || true)
  if [ "${#GPIDS[@]}" -gt 0 ]; then
    log_warn "Killing stray GPU PIDs: ${GPIDS[*]}"
    for p in "${GPIDS[@]}"; do
      kill -TERM "$p" 2>/dev/null || true
    done
    sleep 2
    for p in "${GPIDS[@]}"; do
      kill -KILL "$p" 2>/dev/null || true
    done
  fi

  if [ "${HARD_RESET}" = "1" ]; then
    log_warn "Attempting GPU reset (will fail if any process still holds the GPU or if not permitted)"
    nvidia-smi --gpu-reset || true
  fi
else
  log_warn "nvidia-smi not found; skipping GPU process check"
fi

# 2) Uninstall Python deps we installed
if [ -f "${ROOT_DIR}/requirements.txt" ]; then
  log_info "Uninstalling pip packages from requirements.txt"
  python -m pip uninstall -y -r "${ROOT_DIR}/requirements.txt" || true
else
  log_warn "requirements.txt not found; skipping pip uninstall step"
fi

# 3) Remove virtual envs
for VENV_DIR in "${ROOT_DIR}/.venv" "${ROOT_DIR}/venv" "${ROOT_DIR}/env" "${ROOT_DIR}/.env"; do
  [ -d "$VENV_DIR" ] && { log_info "Removing venv $VENV_DIR"; rm -rf "$VENV_DIR"; }
done

# 4) Clear LMCache disk store (repo-local)
if [ -d "${ROOT_DIR}/.lmcache_store" ]; then
  log_info "Clearing LMCache disk store ${ROOT_DIR}/.lmcache_store"
  rm -rf "${ROOT_DIR}/.lmcache_store"/* || true
fi

# 5) Clear Hugging Face caches (all common locations)
HF_DIRS=(
  "${HF_HOME:-}"
  "${TRANSFORMERS_CACHE:-}"
  "$HOME/.cache/huggingface"
  "/root/.cache/huggingface"
)
for d in "${HF_DIRS[@]}"; do
  [ -n "$d" ] && [ -d "$d" ] && { log_info "Removing HF cache at $d"; rm -rf "$d" || true; }
done

# 6) vLLM / kernel / compiler caches
CACHE_DIRS=(
  "$HOME/.cache/vllm" "/root/.cache/vllm"
  "$HOME/.cache/flashinfer" "/root/.cache/flashinfer"
  "$HOME/.cache/torch/inductor" "/root/.cache/torch/inductor"
  "$HOME/.torch_inductor" "/root/.torch_inductor"
  "$HOME/.cache/torch_extensions" "/root/.cache/torch_extensions"
  "$HOME/.triton" "/root/.triton"
)
for d in "${CACHE_DIRS[@]}"; do
  [ -d "$d" ] && { log_info "Removing cache at $d"; rm -rf "$d" || true; }
done

# 7) Torch + pip caches
log_info "Purging pip cache"
python -m pip cache purge || true
for PIP_CACHE in "$HOME/.cache/pip" "/root/.cache/pip"; do
  [ -d "$PIP_CACHE" ] && rm -rf "$PIP_CACHE" || true
done

for TORCH_CACHE in "$HOME/.cache/torch" "/root/.cache/torch"; do
  [ -d "$TORCH_CACHE" ] && { log_info "Removing torch cache at $TORCH_CACHE"; rm -rf "$TORCH_CACHE" || true; }
done

# 8) NVIDIA PTX JIT cache
for NV_CACHE in "$HOME/.nv/ComputeCache" "/root/.nv/ComputeCache"; do
  [ -d "$NV_CACHE" ] && { log_info "Removing NVIDIA ComputeCache at $NV_CACHE"; rm -rf "$NV_CACHE" || true; }
done

# 9) Project __pycache__ / pytest
log_info "Removing __pycache__ and .pytest_cache in repo"
find "${ROOT_DIR}" -type d -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true
find "${ROOT_DIR}" -type d -name ".pytest_cache" -prune -exec rm -rf {} + 2>/dev/null || true

# 10) Legacy LMCache paths
[ -f "/workspace/lmcache.yaml" ] && { log_info "Removing legacy /workspace/lmcache.yaml"; rm -f /workspace/lmcache.yaml || true; }
[ -d "/workspace/lmcache_store" ] && { log_info "Removing legacy /workspace/lmcache_store"; rm -rf /workspace/lmcache_store || true; }

# 11) Clean server artifacts
rm -f "${ROOT_DIR}/server.log" "${ROOT_DIR}/server.pid" || true

log_info "Done. Repo preserved. Jupyter/console/container remain running."
