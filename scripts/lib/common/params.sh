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


