#!/usr/bin/env bash

# Deployment selection: allow chat-only, tool-only, or both (default both)
export DEPLOY_MODELS=${DEPLOY_MODELS:-both}
case "${DEPLOY_MODELS}" in
  both|chat|tool) ;;
  *) log_warn "Invalid DEPLOY_MODELS='${DEPLOY_MODELS}', defaulting to 'both'"; export DEPLOY_MODELS=both;;
esac

# Convenience flags
DEPLOY_CHAT=0; DEPLOY_TOOL=0
if [ "${DEPLOY_MODELS}" = "both" ] || [ "${DEPLOY_MODELS}" = "chat" ]; then DEPLOY_CHAT=1; fi
if [ "${DEPLOY_MODELS}" = "both" ] || [ "${DEPLOY_MODELS}" = "tool" ]; then DEPLOY_TOOL=1; fi
export DEPLOY_CHAT DEPLOY_TOOL

# Only set defaults for the engines that are actually being deployed
if [ "${DEPLOY_CHAT}" = "1" ]; then
  export AWQ_CHAT_MODEL=${AWQ_CHAT_MODEL:-yapwithai/impish-12b-awq}
fi
if [ "${DEPLOY_TOOL}" = "1" ]; then
  export AWQ_TOOL_MODEL=${AWQ_TOOL_MODEL:-yapwithai/hammer-2.1-3b-awq}
fi

if [ "${DEPLOY_CHAT}" = "1" ] || [ "${DEPLOY_TOOL}" = "1" ]; then
  log_info "AWQ models configured:"
  if [ "${DEPLOY_CHAT}" = "1" ]; then
    log_info "  Chat: ${AWQ_CHAT_MODEL:-none}"
  fi
  if [ "${DEPLOY_TOOL}" = "1" ]; then
    log_info "  Tool: ${AWQ_TOOL_MODEL:-none}"
  fi
  log_info "  Runtime quantization: 4-bit W4A16 compressed tensors (llmcompressor exports autodetected by vLLM)"
fi

# Validate AWQ models for enabled engines when QUANTIZATION=awq
if [ "${QUANTIZATION:-awq}" = "awq" ]; then
  if [ "${DEPLOY_CHAT}" = "1" ] && [ -z "${AWQ_CHAT_MODEL:-}" ]; then
    log_error "Error: AWQ_CHAT_MODEL must be set when deploying chat in AWQ mode"
    exit 1
  fi
  if [ "${DEPLOY_TOOL}" = "1" ] && [ -z "${AWQ_TOOL_MODEL:-}" ]; then
    log_error "Error: AWQ_TOOL_MODEL must be set when deploying tool in AWQ mode"
    exit 1
  fi
fi

# Set model paths/quantization only for selected engines
if [ "${QUANTIZATION:-awq}" = "awq" ]; then
  if [ "${DEPLOY_CHAT}" = "1" ]; then
    export CHAT_MODEL="${AWQ_CHAT_MODEL}"
    export CHAT_QUANTIZATION=awq
  fi
  if [ "${DEPLOY_TOOL}" = "1" ]; then
    export TOOL_MODEL="${AWQ_TOOL_MODEL}"
    export TOOL_QUANTIZATION=awq
  fi
fi


