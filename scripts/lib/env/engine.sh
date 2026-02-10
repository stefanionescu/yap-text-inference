#!/usr/bin/env bash
# shellcheck disable=SC1091
# =============================================================================
# Engine-Level Configuration
# =============================================================================
# Applies engine-specific defaults for vLLM and TRT-LLM. Most vLLM settings
# are handled in Python; this module handles shell-level configuration.

apply_engine_defaults() {
  # vLLM engine settings are handled by Python in src/server.py and
  # src/engines/vllm/setup.py using os.environ.setdefault().
  # This includes VLLM_USE_V1, ENFORCE_EAGER, etc.

  export AWQ_CACHE_DIR="${ROOT_DIR}/.awq"

  # Backend selection is centralized in Python. Only export if explicitly set.
  if [ -n "${VLLM_ATTENTION_BACKEND:-}" ]; then
    export VLLM_ATTENTION_BACKEND
  fi

  # TRT engine: load cached engine directory if available
  if [ "${INFERENCE_ENGINE:-vllm}" = "trt" ]; then
    local trt_env_file="${ROOT_DIR}/.run/trt_engine_dir.env"
    if [ -f "${trt_env_file}" ]; then
      # shellcheck disable=SC1090
      source "${trt_env_file}"
      # TRT_ENGINE_DIR is exported directly by the env file
    fi
  fi
}
