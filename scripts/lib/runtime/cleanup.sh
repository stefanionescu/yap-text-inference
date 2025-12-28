#!/usr/bin/env bash

# Shared cleanup helpers used by stop.sh and runtime guard utilities.

_CLEANUP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${_CLEANUP_DIR}/../common/log.sh"
source "${_CLEANUP_DIR}/../deps/venv.sh"

_cleanup_remove_dirs() {
  local label="$1"; shift
  local dir
  for dir in "$@"; do
    [ -z "${dir}" ] && continue
    [ -e "${dir}" ] && rm -rf "${dir}" || true
  done
}

cleanup_repo_hf_cache() {
  local root_dir="$1"
  _cleanup_remove_dirs "repo hf cache" "${root_dir}/.hf"
}

cleanup_repo_pip_cache() {
  local root_dir="$1"
  _cleanup_remove_dirs "repo pip cache" "${root_dir}/.pip_cache"
}

cleanup_repo_runtime_caches() {
  local root_dir="$1"
  _cleanup_remove_dirs "repo runtime cache" \
    "${root_dir}/.vllm_cache" \
    "${root_dir}/.flashinfer" \
    "${root_dir}/.xformers" \
    "${root_dir}/.trt_cache" \
    "${root_dir}/.torch_inductor" \
    "${root_dir}/.triton"
}

cleanup_repo_engine_artifacts() {
  local root_dir="$1"
  _cleanup_remove_dirs "engine artifact" \
    "${root_dir}/.awq" \
    "${root_dir}/.trtllm-repo" \
    "${root_dir}/models"
}

cleanup_system_vllm_caches() {
  _cleanup_remove_dirs "cache" \
    "$HOME/.cache/vllm" "/root/.cache/vllm" "/workspace/.cache/vllm" \
    "$HOME/.cache/flashinfer" "/root/.cache/flashinfer" "/workspace/.cache/flashinfer"
}

cleanup_system_trt_caches() {
  _cleanup_remove_dirs "cache" \
    "$HOME/.cache/tensorrt_llm" "/root/.cache/tensorrt_llm" \
    "$HOME/.cache/tensorrt" "/root/.cache/tensorrt" \
    "$HOME/.cache/nvidia" "/root/.cache/nvidia" \
    "$HOME/.cache/modelopt" "/root/.cache/modelopt" \
    "$HOME/.cache/onnx" "/root/.cache/onnx" \
    "$HOME/.cache/cuda" "/root/.cache/cuda" \
    "$HOME/.cache/pycuda" "/root/.cache/pycuda" \
    "$HOME/.local/share/tensorrt_llm" "/root/.local/share/tensorrt_llm" \
    "/workspace/.cache/tensorrt" "/workspace/.cache/tensorrt_llm"
}

cleanup_system_compiler_caches() {
  _cleanup_remove_dirs "cache" \
    "$HOME/.cache/torch" "/root/.cache/torch" "/workspace/.cache/torch" \
    "$HOME/.cache/torch_extensions" "/root/.cache/torch_extensions" \
    "$HOME/.torch_inductor" "/root/.torch_inductor" "/workspace/.cache/triton" \
    "$HOME/.triton" "/root/.triton"
}

cleanup_system_nvidia_caches() {
  _cleanup_remove_dirs "cache" "$HOME/.nv" "/root/.nv"
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
  cleanup_repo_hf_cache "${root_dir}"
  cleanup_repo_pip_cache "${root_dir}"
  cleanup_repo_runtime_caches "${root_dir}"
  cleanup_repo_engine_artifacts "${root_dir}"
}

cleanup_runtime_state() {
  local root_dir="$1"
  [ -d "${root_dir}/.run" ] && rm -rf "${root_dir}/.run" || true
}

cleanup_venvs() {
  local root_dir="$1"
  
  # Use get_venv_dir() to detect the actual venv location (handles /opt/venv for Docker)
  local detected_venv
  detected_venv="$(get_venv_dir)"
  
  # Clean detected venv first (could be /opt/venv or repo-local)
  if [ -n "${detected_venv}" ] && [ -d "${detected_venv}" ]; then
    log_info "[cleanup] Removing detected venv: ${detected_venv}"
    rm -rf "${detected_venv}" || true
  fi
  
  local quant_venv
  quant_venv="${QUANT_VENV_DIR:-$(get_quant_venv_dir)}"
  if [ -n "${quant_venv}" ] && [ -d "${quant_venv}" ]; then
    log_info "[cleanup] Removing quantization venv: ${quant_venv}"
    rm -rf "${quant_venv}" || true
  fi
  
  # Also clean all possible repo-local venv locations
  _cleanup_remove_dirs "venv" \
    "${root_dir}/.venv" \
    "${root_dir}/.venv-trt" \
    "${root_dir}/.venv-vllm" \
    "${root_dir}/.venv-quant" \
    "${root_dir}/venv" \
    "${root_dir}/env" \
    "${root_dir}/.env"
  
  # Clean /opt/venv if it exists (Docker prebaked venv)
  if [ -d "/opt/venv" ]; then
    log_info "[cleanup] Removing Docker venv: /opt/venv"
    rm -rf "/opt/venv" || true
  fi
  if [ -d "/opt/venv-quant" ]; then
    log_info "[cleanup] Removing Docker quant venv: /opt/venv-quant"
    rm -rf "/opt/venv-quant" || true
  fi
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
  cleanup_repo_engine_artifacts "${root_dir}"
  cleanup_repo_runtime_caches "${root_dir}"
  cleanup_venvs "${root_dir}"
}

cleanup_misc_caches() {
  cleanup_system_vllm_caches
  cleanup_system_trt_caches
  cleanup_system_compiler_caches
  cleanup_system_nvidia_caches
  _cleanup_remove_dirs "cache" \
    "/workspace/.cache/huggingface" \
    "/workspace/.cache/pip"
}

cleanup_pip_caches() {
  # Use the detected venv python if available
  local venv_python
  venv_python="$(get_venv_python)"
  
  # Try venv python first, then fall back to system python
  local py_cmd=""
  if [ -x "${venv_python}" ]; then
    py_cmd="${venv_python}"
  elif command -v python3 >/dev/null 2>&1; then
    py_cmd="python3"
  elif command -v python >/dev/null 2>&1; then
    py_cmd="python"
  fi
  
  if [ -n "${py_cmd}" ]; then
    "${py_cmd}" -m pip cache purge >/dev/null 2>&1 || true
    local sys_cache
    sys_cache=$("${py_cmd}" -m pip cache dir 2>/dev/null || true)
    [ -n "${sys_cache}" ] && [ -d "${sys_cache}" ] && rm -rf "${sys_cache}" || true
  fi
  
  _cleanup_remove_dirs "pip cache" \
    "$HOME/.cache/pip" "/root/.cache/pip" "/workspace/.cache/pip" "${PIP_CACHE_DIR:-}"
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
