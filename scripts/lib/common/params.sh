#!/usr/bin/env bash

# Common params validation helpers.
# Expects log_err/log_warn/log_info to be available from log.sh.

ensure_required_env_vars() {
  local has_errors=0

  if [ -z "${TEXT_API_KEY:-}" ]; then
    log_err "[env] ✗ TEXT_API_KEY environment variable is required before running this script."
    log_err "[env] ✗ Set it with: export TEXT_API_KEY='your_server_api_key'"
    has_errors=1
  fi

  if [ -z "${HF_TOKEN:-}" ]; then
    if [ -n "${HUGGINGFACE_HUB_TOKEN:-}" ]; then
      HF_TOKEN="${HUGGINGFACE_HUB_TOKEN}"
    else
      log_err "[env] ✗ HF_TOKEN (or HUGGINGFACE_HUB_TOKEN) environment variable is required to access Hugging Face models."
      log_err "[env] ✗ Set it with: export HF_TOKEN='hf_xxx'"
      has_errors=1
    fi
  fi

  if [ -z "${MAX_CONCURRENT_CONNECTIONS:-}" ]; then
    log_err "[env] ✗ MAX_CONCURRENT_CONNECTIONS environment variable must be explicitly set."
    log_err "[env] ✗ Choose a capacity that matches your deployment and run: export MAX_CONCURRENT_CONNECTIONS=<number>"
    has_errors=1
  elif ! [[ "${MAX_CONCURRENT_CONNECTIONS}" =~ ^[0-9]+$ ]]; then
    log_err "[env] ✗ MAX_CONCURRENT_CONNECTIONS must be an integer but was '${MAX_CONCURRENT_CONNECTIONS}'."
    has_errors=1
  fi

  if [ "${has_errors}" -ne 0 ]; then
    exit 1
  fi

  export TEXT_API_KEY
  export HF_TOKEN
  export MAX_CONCURRENT_CONNECTIONS
}

# Determine whether the selected quantization represents an uploadable export.
# Accepts explicit quant values (awq, gptq_marlin, fp8, int8_sq, etc.)
# and falls back to QUANT_MODE when specific quant strings are unset.
push_quant_is_supported_quant() {
  local quant="${1:-${QUANTIZATION:-}}"
  local chat_quant="${2:-${CHAT_QUANTIZATION:-}}"

  _push_quant_value_is_supported "${quant}" && return 0
  _push_quant_value_is_supported "${chat_quant}" && return 0

  case "${QUANT_MODE:-}" in
    4bit|8bit)
      return 0
      ;;
  esac
  return 1
}

_push_quant_value_is_supported() {
  local value="$1"
  if [ -z "${value}" ]; then
    return 1
  fi
  value="$(printf '%s' "${value}" | tr '[:upper:]' '[:lower:]')"
  case "${value}" in
    awq|gptq|gptq_marlin|4bit|int4_*|fp4)
      return 0
      ;;
    8bit|fp8|fp8_*|int8_sq|int8|int8_*)
      return 0
      ;;
  esac
  return 1
}

# Honor --push-quant only when a supported quantization (4-bit or 8-bit) is selected.
# Sets HF_AWQ_PUSH to 1 only when requested AND quantization is supported.
# Otherwise HF_AWQ_PUSH is forced to 0 and a skip message is logged.
push_quant_apply_policy() {
  local quant="${1:-${QUANTIZATION:-}}"
  local chat_quant="${2:-${CHAT_QUANTIZATION:-}}"
  local context="${3:-push}"
  local requested="${HF_AWQ_PUSH_REQUESTED:-${HF_AWQ_PUSH:-0}}"

  if [ "${requested}" != "1" ]; then
    HF_AWQ_PUSH=0
    export HF_AWQ_PUSH
    return 0
  fi

  if ! push_quant_is_supported_quant "${quant}" "${chat_quant}"; then
    HF_AWQ_PUSH=0
    export HF_AWQ_PUSH
    log_info "[${context}] --push-quant requested but quantization is not a 4bit/8bit export; skipping Hugging Face push."
    return 0
  fi

  HF_AWQ_PUSH=1
  export HF_AWQ_PUSH
  return 0
}

# Validate required params when --push-quant flag is set
# Must be called after HF_AWQ_PUSH and INFERENCE_ENGINE are set
# Usage: validate_push_quant_prereqs <deploy_mode>
validate_push_quant_prereqs() {
  if [ "${HF_AWQ_PUSH:-0}" != "1" ]; then
    return 0
  fi
  
  local has_errors=0
  
  # HF_TOKEN is required for any push
  if [ -z "${HF_TOKEN:-}" ]; then
    log_err "[env] ✗ --push-quant requires HF_TOKEN (or HUGGINGFACE_HUB_TOKEN) to be set."
    log_err "[env] ✗ Set it with: export HF_TOKEN='hf_xxx'"
    has_errors=1
  fi
  
  # HF_PUSH_REPO_ID is required (unified for both engines)
  if [ -z "${HF_PUSH_REPO_ID:-}" ]; then
    log_err "[env] ✗ --push-quant requires HF_PUSH_REPO_ID to be set."
    log_err "[env] ✗ Set it with: export HF_PUSH_REPO_ID='your-org/model-awq'"
    has_errors=1
  fi
  
  # Validate HF_PUSH_PRIVATE if set (must be 0 or 1)
  if [ -n "${HF_PUSH_PRIVATE:-}" ] && [[ ! "${HF_PUSH_PRIVATE}" =~ ^[01]$ ]]; then
    log_err "[env] ✗ HF_PUSH_PRIVATE must be 0 (public) or 1 (private), got: ${HF_PUSH_PRIVATE}"
    has_errors=1
  fi
  
  if [ "${has_errors}" -ne 0 ]; then
    log_blank
    log_err "[env] ✗ Either provide the required environment variables or remove --push-quant flag."
    exit 1
  fi
  
  # Export push params with defaults
  export HF_PUSH_REPO_ID
  export HF_PUSH_PRIVATE="${HF_PUSH_PRIVATE:-1}"
  
  local visibility="private"
  if [ "${HF_PUSH_PRIVATE}" = "0" ]; then
    visibility="public"
  fi
  log_info "[env] Quantized model will be pushed to ${HF_PUSH_REPO_ID} (${visibility})"
  return 0
}

# Apply --push-engine policy: only enable for TRT engine with prequantized models
# Sets HF_ENGINE_PUSH to 1 only when requested AND using TRT engine.
# Otherwise HF_ENGINE_PUSH is forced to 0 and a skip message is logged.
push_engine_apply_policy() {
  local engine="${1:-${INFERENCE_ENGINE:-trt}}"
  local context="${2:-push}"
  local requested="${HF_ENGINE_PUSH_REQUESTED:-${HF_ENGINE_PUSH:-0}}"

  if [ "${requested}" != "1" ]; then
    HF_ENGINE_PUSH=0
    export HF_ENGINE_PUSH
    return 0
  fi

  # Only TRT engine supports engine-only push
  if [ "${engine}" != "trt" ]; then
    HF_ENGINE_PUSH=0
    export HF_ENGINE_PUSH
    log_info "[${context}] --push-engine is only supported for TensorRT engine; ignoring for vLLM."
    return 0
  fi

  HF_ENGINE_PUSH=1
  export HF_ENGINE_PUSH
  return 0
}

# Validate required params when --push-engine flag is set
# Must be called after HF_ENGINE_PUSH is set
# Usage: validate_push_engine_prereqs
validate_push_engine_prereqs() {
  if [ "${HF_ENGINE_PUSH:-0}" != "1" ]; then
    return 0
  fi
  
  local has_errors=0
  
  # HF_TOKEN is required for any push
  if [ -z "${HF_TOKEN:-}" ]; then
    log_err "[env] ✗ --push-engine requires HF_TOKEN (or HUGGINGFACE_HUB_TOKEN) to be set."
    log_err "[env] ✗ Set it with: export HF_TOKEN='hf_xxx'"
    has_errors=1
  fi
  
  if [ "${has_errors}" -ne 0 ]; then
    log_blank
    log_err "[env] ✗ Either provide HF_TOKEN or remove --push-engine flag."
    exit 1
  fi
  
  log_info "[env] Engine will be pushed to source HuggingFace repo after build"
  return 0
}
