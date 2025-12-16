#!/usr/bin/env bash

# Common params validation helpers.
# Expects log_error/log_warn/log_info to be available from log.sh.

ensure_required_env_vars() {
  local has_errors=0

  if [ -z "${TEXT_API_KEY:-}" ]; then
    log_error "TEXT_API_KEY environment variable is required before running this script."
    log_error "Set it with: export TEXT_API_KEY='your_server_api_key'"
    has_errors=1
  fi

  if [ -z "${HF_TOKEN:-}" ]; then
    if [ -n "${HUGGINGFACE_HUB_TOKEN:-}" ]; then
      HF_TOKEN="${HUGGINGFACE_HUB_TOKEN}"
    else
      log_error "HF_TOKEN (or HUGGINGFACE_HUB_TOKEN) environment variable is required to access Hugging Face models."
      log_error "Set it with: export HF_TOKEN='hf_xxx'"
      has_errors=1
    fi
  fi

  if [ -z "${MAX_CONCURRENT_CONNECTIONS:-}" ]; then
    log_error "MAX_CONCURRENT_CONNECTIONS environment variable must be explicitly set."
    log_error "Choose a capacity that matches your deployment and run: export MAX_CONCURRENT_CONNECTIONS=<number>"
    has_errors=1
  elif ! [[ "${MAX_CONCURRENT_CONNECTIONS}" =~ ^[0-9]+$ ]]; then
    log_error "MAX_CONCURRENT_CONNECTIONS must be an integer but was '${MAX_CONCURRENT_CONNECTIONS}'."
    has_errors=1
  fi

  if [ "${has_errors}" -ne 0 ]; then
    exit 1
  fi

  export TEXT_API_KEY
  export HF_TOKEN
  export MAX_CONCURRENT_CONNECTIONS
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
    log_error "--push-quant requires HF_TOKEN (or HUGGINGFACE_HUB_TOKEN) to be set."
    log_error "Set it with: export HF_TOKEN='hf_xxx'"
    has_errors=1
  fi
  
  # Check engine-specific repo requirements
  local engine="${INFERENCE_ENGINE:-vllm}"
  
  if [ "${engine}" = "trt" ]; then
    # TRT requires TRT_HF_PUSH_REPO_ID
    if [ -z "${TRT_HF_PUSH_REPO_ID:-}" ]; then
      log_error "--push-quant with TRT engine requires TRT_HF_PUSH_REPO_ID to be set."
      log_error "Set it with: export TRT_HF_PUSH_REPO_ID='your-org/chat-trt-awq'"
      has_errors=1
    fi
  else
    # vLLM requires HF_AWQ_CHAT_REPO for chat/both modes
    local need_chat=0
    case "${deploy_mode}" in
      both|chat) need_chat=1 ;;
    esac
    
    if [ "${need_chat}" = "1" ]; then
      if [ -z "${HF_AWQ_CHAT_REPO:-}" ] || [[ "${HF_AWQ_CHAT_REPO}" == your-org/* ]]; then
        log_error "--push-quant requires HF_AWQ_CHAT_REPO to point to your Hugging Face chat repo."
        log_error "Set it with: export HF_AWQ_CHAT_REPO='your-org/chat-awq'"
        has_errors=1
      fi
    fi
  fi
  
  if [ "${has_errors}" -ne 0 ]; then
    log_error ""
    log_error "Either provide the required environment variables or remove --push-quant flag."
    exit 1
  fi
  
  log_info "--push-quant enabled: quantized models will be pushed to Hugging Face after build"
  return 0
}


