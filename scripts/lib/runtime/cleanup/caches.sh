#!/usr/bin/env bash
# =============================================================================
# Runtime Cleanup - Caches
# =============================================================================

cleanup_repo_hf_cache() {
  local root_dir="$1"
  _cleanup_remove_dirs "${root_dir}/.hf"
}

cleanup_repo_pip_cache() {
  local root_dir="$1"
  _cleanup_remove_dirs "${root_dir}/.pip_cache"
}

cleanup_repo_runtime_caches() {
  local root_dir="$1"
  _cleanup_remove_dirs \
    "${root_dir}/.vllm_cache" \
    "${root_dir}/.flashinfer" \
    "${root_dir}/.xformers" \
    "${root_dir}/.trt_cache" \
    "${root_dir}/.torch_inductor" \
    "${root_dir}/.triton"
}

cleanup_repo_engine_artifacts() {
  local root_dir="$1"
  _cleanup_remove_dirs \
    "${root_dir}/.awq" \
    "${root_dir}/.trtllm-repo" \
    "${root_dir}/models"
}

cleanup_system_vllm_caches() {
  _cleanup_remove_dirs \
    "$HOME/.cache/vllm" "/root/.cache/vllm" "/workspace/.cache/vllm" \
    "$HOME/.cache/flashinfer" "/root/.cache/flashinfer" "/workspace/.cache/flashinfer"
}

cleanup_system_trt_caches() {
  _cleanup_remove_dirs \
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
  _cleanup_remove_dirs \
    "$HOME/.cache/torch" "/root/.cache/torch" "/workspace/.cache/torch" \
    "$HOME/.cache/torch_extensions" "/root/.cache/torch_extensions" \
    "$HOME/.torch_inductor" "/root/.torch_inductor" "/workspace/.cache/triton" \
    "$HOME/.triton" "/root/.triton"
}

cleanup_system_nvidia_caches() {
  _cleanup_remove_dirs "$HOME/.nv" "/root/.nv"
}

cleanup_repo_caches() {
  local root_dir="$1"
  cleanup_repo_hf_cache "${root_dir}"
  cleanup_repo_pip_cache "${root_dir}"
  cleanup_repo_runtime_caches "${root_dir}"
  cleanup_repo_engine_artifacts "${root_dir}"
}

cleanup_hf_caches() {
  _cleanup_remove_dirs \
    "${HF_HOME:-}" \
    "${TRANSFORMERS_CACHE:-}" \
    "${HUGGINGFACE_HUB_CACHE:-}" \
    "$HOME/.cache/huggingface" \
    "$HOME/.cache/huggingface/hub" \
    "/root/.cache/huggingface" \
    "/root/.cache/huggingface/hub"

  _cleanup_remove_dirs \
    "$HOME/.huggingface" "/root/.huggingface" \
    "$HOME/.config/huggingface" "/root/.config/huggingface" \
    "$HOME/.local/share/huggingface" "/root/.local/share/huggingface"
}

cleanup_misc_caches() {
  cleanup_system_vllm_caches
  cleanup_system_trt_caches
  cleanup_system_compiler_caches
  cleanup_system_nvidia_caches
  _cleanup_remove_dirs \
    "/workspace/.cache/huggingface" \
    "/workspace/.cache/pip"
}

cleanup_pip_caches() {
  local venv_python
  venv_python="$(get_venv_python)"

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
    if [ -n "${sys_cache}" ] && [ -d "${sys_cache}" ]; then
      rm -rf "${sys_cache}"
    fi
  fi

  _cleanup_remove_dirs \
    "$HOME/.cache/pip" "/root/.cache/pip" "/workspace/.cache/pip" "${PIP_CACHE_DIR:-}"
}

cleanup_home_cache_roots() {
  _cleanup_remove_dirs "$HOME/.cache" "/root/.cache"
  if [ -n "${XDG_CACHE_HOME:-}" ] && [ -d "${XDG_CACHE_HOME}" ]; then
    rm -rf "${XDG_CACHE_HOME}"
  fi
}
