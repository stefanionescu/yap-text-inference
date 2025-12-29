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

# Determine whether the selected quantization represents a 4-bit export
# Accepts explicit quant values (awq, gptq_marlin, int4_*)
# and falls back to QUANT_MODE=4bit when specific quant strings are unset.
push_quant_is_4bit() {
  local quant="${1:-${QUANTIZATION:-}}"
  local chat_quant="${2:-${CHAT_QUANTIZATION:-}}"

  case "${quant}" in
    awq|gptq|gptq_marlin|4bit|int4_*|fp4) return 0 ;;
  esac
  case "${chat_quant}" in
    awq|gptq|gptq_marlin|4bit|int4_*|fp4) return 0 ;;
  esac
  if [ "${QUANT_MODE:-}" = "4bit" ]; then
    return 0
  fi
  return 1
}

# Honor --push-quant only when a 4-bit quantization is selected.
# Sets HF_AWQ_PUSH to 1 only when requested AND quantization is 4-bit.
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

  if ! push_quant_is_4bit "${quant}" "${chat_quant}"; then
    HF_AWQ_PUSH=0
    export HF_AWQ_PUSH
    log_info "[${context}] --push-quant requested but quantization is not 4bit; skipping Hugging Face push."
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
  local deploy_mode="${1:-both}"
  
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

