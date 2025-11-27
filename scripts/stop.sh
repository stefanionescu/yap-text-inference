#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/lib/common/log.sh"

HARD_RESET="${HARD_RESET:-0}"   # set HARD_RESET=1 to attempt nvidia-smi --gpu-reset
SERVER_PID_FILE="${ROOT_DIR}/server.pid"
DEPLOYMENT_PID_FILE="${ROOT_DIR}/.run/deployment.pid"
WARMUP_LOCK_FILE="${ROOT_DIR}/.run/warmup.lock"

# Default to deepest cleanup unless explicitly opted out (NUKE_ALL=0)
NUKE_ALL="${NUKE_ALL:-1}"

log_info "Wiping runtime deps and caches; keeping repo and container services alive"

# Helper to kill a process session by PID file
_kill_pid_file_session() {
  local pid_file="$1"
  local description="$2"
  
  if [ ! -f "${pid_file}" ]; then
    return 1
  fi
  
  local pid
  pid="$(cat "${pid_file}" 2>/dev/null)" || true
  if [ -z "${pid:-}" ]; then
    rm -f "${pid_file}" || true
    return 1
  fi
  
  if ! ps -p "${pid}" >/dev/null 2>&1; then
    log_info "Stale ${description} PID file (process ${pid} not running)"
    rm -f "${pid_file}" || true
    return 1
  fi
  
  log_info "Stopping ${description} session (PID ${pid})"
  # Kill the whole process group/session
  kill -TERM -"${pid}" 2>/dev/null || kill -TERM "${pid}" 2>/dev/null || true
  
  # Graceful wait up to 10s
  local waited=0
  while [ "${waited}" -lt 10 ] && ps -p "${pid}" >/dev/null 2>&1; do
    sleep 1
    waited=$((waited + 1))
  done
  
  # Hard kill if still alive
  if ps -p "${pid}" >/dev/null 2>&1; then
    log_warn "${description} still alive after 10s, forcing kill"
    kill -KILL -"${pid}" 2>/dev/null || kill -KILL "${pid}" 2>/dev/null || true
  fi
  
  rm -f "${pid_file}" || true
  return 0
}

# 0) Stop deployment pipeline (includes quantization) if running
if _kill_pid_file_session "${DEPLOYMENT_PID_FILE}" "deployment pipeline"; then
  log_info "Deployment pipeline stopped"
fi

# 1) Stop server + ALL its children (vLLM workers) = free VRAM
if _kill_pid_file_session "${SERVER_PID_FILE}" "server"; then
  log_info "Server stopped"
else
  log_info "No server.pid; best-effort kill by pattern"
  pkill -f "uvicorn src.server:app" || true
fi

# 2) Stop warmup process if running
if [ -f "${WARMUP_LOCK_FILE}" ]; then
  warmup_pid="$(cat "${WARMUP_LOCK_FILE}" 2>/dev/null)" || true
  if [ -n "${warmup_pid:-}" ] && ps -p "${warmup_pid}" >/dev/null 2>&1; then
    log_info "Stopping warmup process (PID ${warmup_pid})"
    kill -TERM "${warmup_pid}" 2>/dev/null || true
    sleep 2
    ps -p "${warmup_pid}" >/dev/null 2>&1 && kill -KILL "${warmup_pid}" 2>/dev/null || true
  fi
  rm -f "${WARMUP_LOCK_FILE}" || true
fi

# 3) Kill any orphan processes by pattern
log_info "Killing orphan processes by pattern..."

# vLLM engine workers
pkill -f "vllm.v1.engine.core" || true
pkill -f "EngineCore_0" || true
pkill -f "python.*vllm" || true

# AWQ quantization processes
pkill -f "src.awq.quantize" || true
pkill -f "python.*awq" || true
pkill -f "autoawq" || true

# Any remaining server/test processes
pkill -f "uvicorn src.server" || true
pkill -f "test/warmup.py" || true
pkill -f "test/bench.py" || true

sleep 1

# 4) Remove repo-local caches (models and compiled artifacts under the repo)
if [ "${NUKE_ALL}" != "0" ]; then
  REPO_CACHE_DIRS=(
    "${ROOT_DIR}/.hf"
    "${ROOT_DIR}/.vllm_cache"
    "${ROOT_DIR}/.torch_inductor"
    "${ROOT_DIR}/.triton"
    "${ROOT_DIR}/.flashinfer"
    "${ROOT_DIR}/.xformers"
    "${ROOT_DIR}/.pip_cache"
    "${ROOT_DIR}/.awq"
  )
  for d in "${REPO_CACHE_DIRS[@]}"; do
    [ -d "$d" ] && { log_info "Removing repo cache at $d"; rm -rf "$d" || true; }
  done
else
  log_info "NUKE_ALL=0: preserving repo caches and models under ${ROOT_DIR}"
fi

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

# 2) Remove virtual env(s) by default (unless NUKE_ALL=0)
if [ "${NUKE_ALL}" != "0" ]; then
  for VENV_DIR in "${ROOT_DIR}/.venv" "${ROOT_DIR}/venv" "${ROOT_DIR}/env" "${ROOT_DIR}/.env"; do
    [ -d "$VENV_DIR" ] && { log_info "Removing venv $VENV_DIR"; rm -rf "$VENV_DIR" || true; }
  done
else
  log_info "NUKE_ALL=0: preserving virtualenv(s)"
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
    [ -n "$d" ] && [ -d "$d" ] && { log_info "Removing HF cache at $d"; rm -rf "$d" || true; }
  done
  for HFC in "$HOME/.huggingface" "/root/.huggingface" "$HOME/.config/huggingface" "/root/.config/huggingface" "$HOME/.local/share/huggingface" "/root/.local/share/huggingface"; do
    [ -d "$HFC" ] && { log_warn "Removing HF config at $HFC"; rm -rf "$HFC" || true; }
  done
else
  log_info "NUKE_ALL=0: preserving HF caches/config"
fi

# 4) vLLM / kernel / compiler caches
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

# 5) Torch + pip caches (purge by default unless NUKE_ALL=0)
if [ "${NUKE_ALL}" != "0" ]; then
  # Pip caches
  if command -v python >/dev/null 2>&1; then
    python -m pip cache purge || true
    PIP_SYS_CACHE_DIR=$(python -m pip cache dir 2>/dev/null || true)
    if [ -n "${PIP_SYS_CACHE_DIR}" ] && [ -d "${PIP_SYS_CACHE_DIR}" ]; then
      log_info "Removing pip reported cache at ${PIP_SYS_CACHE_DIR}"
      rm -rf "${PIP_SYS_CACHE_DIR}" || true
    fi
  fi
  for PIP_CACHE in "$HOME/.cache/pip" "/root/.cache/pip" "${PIP_CACHE_DIR:-}"; do
    [ -n "$PIP_CACHE" ] && [ -d "$PIP_CACHE" ] && { log_info "Removing pip cache at $PIP_CACHE"; rm -rf "$PIP_CACHE" || true; }
  done
else
  log_info "NUKE_ALL=0: preserving pip caches"
fi

for TORCH_CACHE in "$HOME/.cache/torch" "/root/.cache/torch"; do
  [ -d "$TORCH_CACHE" ] && { log_info "Removing torch cache at $TORCH_CACHE"; rm -rf "$TORCH_CACHE" || true; }
done

# 6) NVIDIA PTX JIT cache
for NV_CACHE in "$HOME/.nv/ComputeCache" "/root/.nv/ComputeCache"; do
  [ -d "$NV_CACHE" ] && { log_info "Removing NVIDIA ComputeCache at $NV_CACHE"; rm -rf "$NV_CACHE" || true; }
done

# 7) Project __pycache__ / pytest
log_info "Removing __pycache__ and .pytest_cache in repo"
find "${ROOT_DIR}" -type d -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true
find "${ROOT_DIR}" -type d -name ".pytest_cache" -prune -exec rm -rf {} + 2>/dev/null || true

# 8) Temp directories
rm -rf /tmp/vllm* /tmp/flashinfer* /tmp/torch_* /tmp/pip-* /tmp/pip-build-* /tmp/pip-modern-metadata-* /tmp/uvicorn* 2>/dev/null || true

# Remove runtime state directory
if [ -d "${ROOT_DIR}/.run" ]; then
  log_info "Removing runtime state at ${ROOT_DIR}/.run"
  rm -rf "${ROOT_DIR}/.run" || true
fi

# 9) Nuke entire home caches by default (heavy-handed; unless NUKE_ALL=0)
if [ "${NUKE_ALL}" != "0" ]; then
  for C in "$HOME/.cache" "/root/.cache"; do
    [ -d "$C" ] && { log_warn "Removing $C"; rm -rf "$C" || true; }
  done
  if [ -n "${XDG_CACHE_HOME:-}" ] && [ -d "${XDG_CACHE_HOME}" ]; then
    log_warn "Removing XDG cache at ${XDG_CACHE_HOME}"
    rm -rf "${XDG_CACHE_HOME}" || true
  fi
else
  log_info "NUKE_ALL=0: preserving home caches"
fi

# 10) Clean server artifacts
rm -f "${ROOT_DIR}/server.log" "${ROOT_DIR}/server.pid" "${ROOT_DIR}/.server.log.trim" || true

log_info "Done. Repo preserved. Jupyter/console/container remain running."
