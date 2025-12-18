#!/usr/bin/env bash

# Engine-level defaults and backend gating

apply_engine_defaults() {
  # vLLM engine selection; attention backend chosen in Python unless explicitly set here
  export VLLM_USE_V1=${VLLM_USE_V1:-1}
  export ENFORCE_EAGER=${ENFORCE_EAGER:-0}
  export VLLM_ALLOW_LONG_MAX_MODEL_LEN=${VLLM_ALLOW_LONG_MAX_MODEL_LEN:-1}
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
      if [ -n "${TRTLLM_ENGINE_DIR:-}" ]; then
        export TRT_ENGINE_DIR="${TRTLLM_ENGINE_DIR}"
        log_info "[engine] Loaded TRT engine path: ${TRT_ENGINE_DIR}"
      fi
    fi
  fi
}


