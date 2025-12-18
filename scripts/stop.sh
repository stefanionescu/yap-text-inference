#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/lib/common/log.sh"

HARD_RESET="${HARD_RESET:-0}"   # set HARD_RESET=1 to attempt nvidia-smi --gpu-reset
PID_FILE="${ROOT_DIR}/server.pid"

# Default to deepest cleanup unless explicitly opted out (NUKE_ALL=0)
NUKE_ALL="${NUKE_ALL:-1}"

if [ "${NUKE_ALL}" = "0" ]; then
  log_info "[stop] Light stop: preserving venv, caches, and models"
else
  log_info "[stop] Full stop: wiping runtime deps and caches"
fi

# 0) Stop server + ALL its children (vLLM workers) = free VRAM
if [ -f "${PID_FILE}" ]; then
  PID="$(cat "${PID_FILE}")" || true
  if [ -n "${PID:-}" ] && ps -p "${PID}" >/dev/null 2>&1; then
    # uvicorn was started as a session leader via setsid; kill the whole session
    log_info "[stop] Stopping server session (PID ${PID})"
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
  log_info "[stop] No server.pid; best-effort kill by pattern"
  pkill -f "uvicorn src.server:app" || true
fi

# Also kill any orphan vLLM/engine workers just in case
pkill -f "vllm.v1.engine.core" || true
pkill -f "EngineCore_0" || true
pkill -f "python.*vllm" || true

# Kill TensorRT-LLM processes
pkill -f "python.*tensorrt" || true
pkill -f "python.*trtllm" || true
pkill -f "trtllm-build" || true
pkill -f "quantize.py" || true
pkill -f "mpirun" || true
pkill -f "mpi4py" || true
pkill -f "python.*cuda" || true

sleep 1

# 4) Remove repo-local caches (models and compiled artifacts under the repo)
if [ "${NUKE_ALL}" != "0" ]; then
  REPO_CACHE_DIRS=(
    # Common caches
    "${ROOT_DIR}/.hf"
    "${ROOT_DIR}/.pip_cache"
    # vLLM caches
    "${ROOT_DIR}/.vllm_cache"
    "${ROOT_DIR}/.flashinfer"
    "${ROOT_DIR}/.xformers"
    "${ROOT_DIR}/.awq"
    # TRT-LLM caches
    "${ROOT_DIR}/.trtllm-repo"
    "${ROOT_DIR}/.trt_cache"
    "${ROOT_DIR}/models"
    # Compiler caches
    "${ROOT_DIR}/.torch_inductor"
    "${ROOT_DIR}/.triton"
  )
  for d in "${REPO_CACHE_DIRS[@]}"; do
    [ -d "$d" ] && { log_info "[cache] Removing repo cache at $d"; rm -rf "$d" || true; }
  done
  
  # Remove engine-specific venvs
  for venv_suffix in "" "-trt" "-vllm"; do
    venv_path="${ROOT_DIR}/.venv${venv_suffix}"
    [ -d "${venv_path}" ] && { log_info "[cache] Removing venv at ${venv_path}"; rm -rf "${venv_path}" || true; }
  done
fi

# 1) Verify VRAM is free; if not, kill leftover GPU PIDs
if command -v nvidia-smi >/dev/null 2>&1; then
  log_info "[stop] Checking for leftover GPU processes"
  # Get PIDs using the GPU (ignore n/a lines)
  mapfile -t GPIDS < <(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null | awk '{print $1}' | grep -E '^[0-9]+$' || true)
  if [ "${#GPIDS[@]}" -gt 0 ]; then
    log_warn "[stop] Killing stray GPU PIDs: ${GPIDS[*]}"
    for p in "${GPIDS[@]}"; do
      kill -TERM "$p" 2>/dev/null || true
    done
    sleep 2
    for p in "${GPIDS[@]}"; do
      kill -KILL "$p" 2>/dev/null || true
    done
  fi

  if [ "${HARD_RESET}" = "1" ]; then
    log_warn "[stop] Attempting GPU reset (will fail if any process still holds the GPU or if not permitted)"
    nvidia-smi --gpu-reset || true
  fi
else
  log_warn "[stop] nvidia-smi not found; skipping GPU process check"
fi

# 2) Remove virtual env(s) by default (unless NUKE_ALL=0)
if [ "${NUKE_ALL}" != "0" ]; then
  for VENV_DIR in "${ROOT_DIR}/.venv" "${ROOT_DIR}/venv" "${ROOT_DIR}/env" "${ROOT_DIR}/.env"; do
    [ -d "$VENV_DIR" ] && { log_info "[cache] Removing venv $VENV_DIR"; rm -rf "$VENV_DIR" || true; }
  done
fi

# 3) Clear Hugging Face caches and config by default (unless NUKE_ALL=0)
if [ "${NUKE_ALL}" != "0" ]; then
  HF_DIRS=(
    "${HF_HOME:-}"
    "${TRANSFORMERS_CACHE:-}"
    "${HUGGINGFACE_HUB_CACHE:-}"
    "$HOME/.cache/huggingface"
    "$HOME/.cache/huggingface/hub"
    "/root/.cache/huggingface"
    "/root/.cache/huggingface/hub"
  )
  for d in "${HF_DIRS[@]}"; do
    [ -n "$d" ] && [ -d "$d" ] && { log_info "[cache] Removing HF cache at $d"; rm -rf "$d" || true; }
  done
  for HFC in "$HOME/.huggingface" "/root/.huggingface" "$HOME/.config/huggingface" "/root/.config/huggingface" "$HOME/.local/share/huggingface" "/root/.local/share/huggingface"; do
    [ -d "$HFC" ] && { log_warn "[cache] Removing HF config at $HFC"; rm -rf "$HFC" || true; }
  done
fi

# 4) vLLM / TRT-LLM / kernel / compiler caches
CACHE_DIRS=(
  # vLLM caches
  "$HOME/.cache/vllm" "/root/.cache/vllm"
  "$HOME/.cache/flashinfer" "/root/.cache/flashinfer"
  # TRT-LLM caches
  "$HOME/.cache/tensorrt_llm" "/root/.cache/tensorrt_llm"
  "$HOME/.cache/tensorrt" "/root/.cache/tensorrt"
  "$HOME/.cache/nvidia" "/root/.cache/nvidia"
  "$HOME/.cache/modelopt" "/root/.cache/modelopt"
  "$HOME/.cache/onnx" "/root/.cache/onnx"
  "$HOME/.cache/cuda" "/root/.cache/cuda"
  "$HOME/.cache/pycuda" "/root/.cache/pycuda"
  "$HOME/.local/share/tensorrt_llm" "/root/.local/share/tensorrt_llm"
  # Torch / compiler caches
  "$HOME/.cache/torch/inductor" "/root/.cache/torch/inductor"
  "$HOME/.torch_inductor" "/root/.torch_inductor"
  "$HOME/.cache/torch_extensions" "/root/.cache/torch_extensions"
  "$HOME/.triton" "/root/.triton"
  # Container workspace caches (for Docker deployments)
  "/workspace/.cache/huggingface" "/workspace/.cache/pip"
  "/workspace/.cache/torch" "/workspace/.cache/tensorrt"
  "/workspace/.cache/triton" "/workspace/.cache/vllm"
)
for d in "${CACHE_DIRS[@]}"; do
  [ -d "$d" ] && { log_info "[cache] Removing cache at $d"; rm -rf "$d" || true; }
done

# 5) Torch + pip caches (purge by default unless NUKE_ALL=0)
if [ "${NUKE_ALL}" != "0" ]; then
  # Pip caches
  if command -v python >/dev/null 2>&1; then
    python -m pip cache purge || true
    PIP_SYS_CACHE_DIR=$(python -m pip cache dir 2>/dev/null || true)
    if [ -n "${PIP_SYS_CACHE_DIR}" ] && [ -d "${PIP_SYS_CACHE_DIR}" ]; then
      log_info "[cache] Removing pip reported cache at ${PIP_SYS_CACHE_DIR}"
      rm -rf "${PIP_SYS_CACHE_DIR}" || true
    fi
  fi
  for PIP_CACHE in "$HOME/.cache/pip" "/root/.cache/pip" "${PIP_CACHE_DIR:-}"; do
    [ -n "$PIP_CACHE" ] && [ -d "$PIP_CACHE" ] && { log_info "[cache] Removing pip cache at $PIP_CACHE"; rm -rf "$PIP_CACHE" || true; }
  done
fi

for TORCH_CACHE in "$HOME/.cache/torch" "/root/.cache/torch"; do
  [ -d "$TORCH_CACHE" ] && { log_info "[cache] Removing torch cache at $TORCH_CACHE"; rm -rf "$TORCH_CACHE" || true; }
done

# 6) NVIDIA PTX JIT cache and other .nv caches
for NV_CACHE in "$HOME/.nv" "/root/.nv"; do
  [ -d "$NV_CACHE" ] && { log_info "[cache] Removing NVIDIA cache at $NV_CACHE"; rm -rf "$NV_CACHE" || true; }
done

# 7) Project __pycache__ / pytest
log_info "[stop] Removing __pycache__ and .pytest_cache in repo"
find "${ROOT_DIR}" -type d -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true
find "${ROOT_DIR}" -type d -name ".pytest_cache" -prune -exec rm -rf {} + 2>/dev/null || true

# 8a) Temp directories (vLLM + TRT-LLM)
rm -rf /tmp/vllm* /tmp/flashinfer* /tmp/torch_* /tmp/pip-* /tmp/pip-build-* /tmp/pip-modern-metadata-* /tmp/uvicorn* /tmp/trtllm* /tmp/trt* /tmp/tensorrt* /tmp/nv* /tmp/hf* /tmp/cuda* /tmp/modelopt* /tmp/quantiz* 2>/dev/null || true

# 8b) Shared memory (TRT-LLM uses /dev/shm)
rm -rf /dev/shm/tensorrt* /dev/shm/trt* /dev/shm/torch* /dev/shm/nv* /dev/shm/cuda* /dev/shm/hf* 2>/dev/null || true

# 8c) Remove runtime state directory (only in full stop mode)
# Light stop preserves .run/ which contains engine paths, last config, etc.
if [ "${NUKE_ALL}" != "0" ]; then
  if [ -d "${ROOT_DIR}/.run" ]; then
    log_info "[stop] Removing runtime state at ${ROOT_DIR}/.run"
    rm -rf "${ROOT_DIR}/.run" || true
  fi
fi

# 9) Nuke entire home caches by default (heavy-handed; unless NUKE_ALL=0)
if [ "${NUKE_ALL}" != "0" ]; then
  for C in "$HOME/.cache" "/root/.cache"; do
    [ -d "$C" ] && { log_warn "[cache] Removing $C"; rm -rf "$C" || true; }
  done
  if [ -n "${XDG_CACHE_HOME:-}" ] && [ -d "${XDG_CACHE_HOME}" ]; then
    log_warn "[cache] Removing XDG cache at ${XDG_CACHE_HOME}"
    rm -rf "${XDG_CACHE_HOME}" || true
  fi
fi

# 10) Clean server artifacts
rm -f "${ROOT_DIR}/server.log" "${ROOT_DIR}/server.pid" "${ROOT_DIR}/.server.log.trim" || true

log_info "[stop] Done. Repo preserved. Jupyter/console/container remain running."
