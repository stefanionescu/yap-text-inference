#!/usr/bin/env bash

# Set default AWQ models if not provided by user
export AWQ_CHAT_MODEL=${AWQ_CHAT_MODEL:-yapwithai/impish-12b-awq}
export AWQ_TOOL_MODEL=${AWQ_TOOL_MODEL:-yapwithai/hammer-2.1-3b-awq}

if [ -n "${AWQ_CHAT_MODEL:-}" ] || [ -n "${AWQ_TOOL_MODEL:-}" ]; then
  log_info "AWQ models configured:"
  log_info "  Chat: ${AWQ_CHAT_MODEL:-none}"
  log_info "  Tool: ${AWQ_TOOL_MODEL:-none}"
fi

# Always deploy both models in Docker
export DEPLOY_MODELS=both
DEPLOY_CHAT=1
DEPLOY_TOOL=1
export DEPLOY_CHAT DEPLOY_TOOL

# Validate AWQ models only when QUANTIZATION=awq (require both)
if [ "${QUANTIZATION:-awq}" = "awq" ]; then
  if [ -z "${AWQ_CHAT_MODEL:-}" ]; then
    log_error "Error: AWQ_CHAT_MODEL must be set for AWQ mode"
    exit 1
  fi
  if [ -z "${AWQ_TOOL_MODEL:-}" ]; then
    log_error "Error: AWQ_TOOL_MODEL must be set for AWQ mode"
    exit 1
  fi
fi

# Set model paths to AWQ checkpoints when in AWQ mode (always both)
if [ "${QUANTIZATION:-awq}" = "awq" ]; then
  export CHAT_MODEL="${AWQ_CHAT_MODEL}"
  export CHAT_QUANTIZATION=awq
  export TOOL_MODEL="${AWQ_TOOL_MODEL}"
  export TOOL_QUANTIZATION=awq
fi


