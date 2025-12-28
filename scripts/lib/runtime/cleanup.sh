#!/usr/bin/env bash

# Shared cleanup helpers used by stop.sh and runtime guard utilities.

_cleanup_remove_dirs() {
  local label="$1"; shift
  local dir
  for dir in "$@"; do
    [ -z "${dir}" ] && continue
    [ -e "${dir}" ] && rm -rf "${dir}" || true
  done
}

cleanup_stop_server_session() {
  local root_dir="$1"
  local pid_file="${root_dir}/server.pid"

  if [ -f "${pid_file}" ]; then
    local pid
    pid="$(cat "${pid_file}" 2>/dev/null || true)"
    if [ -n "${pid}" ] && ps -p "${pid}" >/dev/null 2>&1; then
      kill -TERM -"${pid}" || true
      for _ in {1..10}; do
        ps -p "${pid}" >/dev/null 2>&1 || break
        sleep 1
      done
      ps -p "${pid}" >/dev/null 2>&1 && kill -KILL -"${pid}" || true
    fi
    rm -f "${pid_file}" || true
  else
    pkill -f "uvicorn src.server:app" || true
  fi
}

cleanup_kill_engine_processes() {
  pkill -f "vllm.v1.engine.core" || true
  pkill -f "EngineCore_0" || true
  pkill -f "python.*vllm" || true
  pkill -f "python.*tensorrt" || true
  pkill -f "python.*trtllm" || true
  pkill -f "trtllm-build" || true
  pkill -f "quantize.py" || true
  pkill -f "mpirun" || true
  pkill -f "mpi4py" || true
  pkill -f "python.*cuda" || true
}

cleanup_repo_caches() {
  local root_dir="$1"
  _cleanup_remove_dirs "repo cache" \
    "${root_dir}/.hf" \
    "${root_dir}/.pip_cache" \
    "${root_dir}/.vllm_cache" \
    "${root_dir}/.flashinfer" \
    "${root_dir}/.xformers" \
    "${root_dir}/.awq" \
    "${root_dir}/.trtllm-repo" \
    "${root_dir}/.trt_cache" \
    "${root_dir}/models" \
    "${root_dir}/.torch_inductor" \
    "${root_dir}/.triton"
}

cleanup_runtime_state() {
  local root_dir="$1"
  [ -d "${root_dir}/.run" ] && rm -rf "${root_dir}/.run" || true
}

cleanup_venvs() {
  local root_dir="$1"
  _cleanup_remove_dirs "venv" \
    "${root_dir}/.venv" \
    "${root_dir}/.venv-trt" \
    "${root_dir}/.venv-vllm" \
    "${root_dir}/venv" \
    "${root_dir}/env" \
    "${root_dir}/.env"
}

cleanup_hf_caches() {
  _cleanup_remove_dirs "HF cache" \
    "${HF_HOME:-}" \
    "${TRANSFORMERS_CACHE:-}" \
    "${HUGGINGFACE_HUB_CACHE:-}" \
    "$HOME/.cache/huggingface" \
    "$HOME/.cache/huggingface/hub" \
    "/root/.cache/huggingface" \
    "/root/.cache/huggingface/hub"

  _cleanup_remove_dirs "HF config" \
    "$HOME/.huggingface" "/root/.huggingface" \
    "$HOME/.config/huggingface" "/root/.config/huggingface" \
    "$HOME/.local/share/huggingface" "/root/.local/share/huggingface"
}

cleanup_engine_artifacts() {
  local root_dir="$1"
  _cleanup_remove_dirs "engine artifact" \
    "${root_dir}/.awq" \
    "${root_dir}/.trtllm-repo" \
    "${root_dir}/.trt_cache" \
    "${root_dir}/models" \
    "${root_dir}/.vllm_cache" \
    "${root_dir}/.flashinfer" \
    "${root_dir}/.xformers" \
    "${root_dir}/.venv" \
    "${root_dir}/.venv-trt" \
    "${root_dir}/.venv-vllm"
}

cleanup_misc_caches() {
  _cleanup_remove_dirs "cache" \
    "$HOME/.cache/vllm" "/root/.cache/vllm" \
    "$HOME/.cache/flashinfer" "/root/.cache/flashinfer" \
    "$HOME/.cache/tensorrt_llm" "/root/.cache/tensorrt_llm" \
    "$HOME/.cache/tensorrt" "/root/.cache/tensorrt" \
    "$HOME/.cache/nvidia" "/root/.cache/nvidia" \
    "$HOME/.cache/modelopt" "/root/.cache/modelopt" \
    "$HOME/.cache/onnx" "/root/.cache/onnx" \
    "$HOME/.cache/cuda" "/root/.cache/cuda" \
    "$HOME/.cache/pycuda" "/root/.cache/pycuda" \
    "$HOME/.local/share/tensorrt_llm" "/root/.local/share/tensorrt_llm" \
    "$HOME/.cache/torch/inductor" "/root/.cache/torch/inductor" \
    "$HOME/.torch_inductor" "/root/.torch_inductor" \
    "$HOME/.cache/torch_extensions" "/root/.cache/torch_extensions" \
    "$HOME/.triton" "/root/.triton" \
    "/workspace/.cache/huggingface" "/workspace/.cache/pip" \
    "/workspace/.cache/torch" "/workspace/.cache/tensorrt" \
    "/workspace/.cache/triton" "/workspace/.cache/vllm"
}

cleanup_pip_caches() {
  if command -v python >/dev/null 2>&1; then
    python -m pip cache purge >/dev/null 2>&1 || true
    local sys_cache
    sys_cache=$(python -m pip cache dir 2>/dev/null || true)
    [ -n "${sys_cache}" ] && [ -d "${sys_cache}" ] && rm -rf "${sys_cache}" || true
  fi
  _cleanup_remove_dirs "pip cache" \
    "$HOME/.cache/pip" "/root/.cache/pip" "${PIP_CACHE_DIR:-}"
}

cleanup_gpu_processes() {
  local hard_reset="${1:-0}"
  command -v nvidia-smi >/dev/null 2>&1 || return 0

  local -a gpids=()
  mapfile -t gpids < <(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null | awk '{print $1}' | grep -E '^[0-9]+$' || true)
  if [ "${#gpids[@]}" -gt 0 ]; then
    local p
    for p in "${gpids[@]}"; do
      kill -TERM "$p" 2>/dev/null || true
    done
    sleep 2
    for p in "${gpids[@]}"; do
      kill -KILL "$p" 2>/dev/null || true
    done
  fi

  [ "${hard_reset}" = "1" ] && nvidia-smi --gpu-reset || true
}

cleanup_tmp_dirs() {
  rm -rf \
    /tmp/vllm* /tmp/flashinfer* /tmp/torch_* /tmp/pip-* /tmp/pip-build-* \
    /tmp/pip-modern-metadata-* /tmp/uvicorn* /tmp/trtllm* /tmp/trt* \
    /tmp/tensorrt* /tmp/nv* /tmp/hf* /tmp/cuda* /tmp/modelopt* /tmp/quantiz* 2>/dev/null || true
  rm -rf /dev/shm/tensorrt* /dev/shm/trt* /dev/shm/torch* /dev/shm/nv* /dev/shm/cuda* /dev/shm/hf* 2>/dev/null || true
}

cleanup_home_cache_roots() {
  _cleanup_remove_dirs "cache root" "$HOME/.cache" "/root/.cache"
  [ -n "${XDG_CACHE_HOME:-}" ] && [ -d "${XDG_CACHE_HOME}" ] && rm -rf "${XDG_CACHE_HOME}" || true
}

cleanup_python_artifacts() {
  local root_dir="$1"
  find "${root_dir}" -type d -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true
  find "${root_dir}" -type d -name ".pytest_cache" -prune -exec rm -rf {} + 2>/dev/null || true
}

cleanup_server_artifacts() {
  local root_dir="$1"
  rm -f "${root_dir}/server.log" "${root_dir}/server.pid" "${root_dir}/.server.log.trim" || true
}


