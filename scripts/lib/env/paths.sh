#!/usr/bin/env bash
# =============================================================================
# Cache and Path Configuration
# =============================================================================
# Configures repository-local cache directories for pip, Hugging Face,
# and quantization artifacts.

set_repo_cache_paths() {
  export PIP_CACHE_DIR="${ROOT_DIR}/.pip_cache"
  export HF_HOME="${ROOT_DIR}/.hf"
  export HUGGINGFACE_HUB_CACHE="${HF_HOME}/hub"
  export VLLM_CACHE_DIR="${ROOT_DIR}/.vllm_cache"
  export TORCHINDUCTOR_CACHE_DIR="${ROOT_DIR}/.torch_inductor"
  export TRITON_CACHE_DIR="${ROOT_DIR}/.triton"
  export FLASHINFER_CACHE_DIR="${ROOT_DIR}/.flashinfer"
  export XFORMERS_CACHE_DIR="${ROOT_DIR}/.xformers"
}


