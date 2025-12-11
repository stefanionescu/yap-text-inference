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
  export CHAT_MODEL=${CHAT_MODEL:-yapwithai/impish-12b-awq}
fi
if [ "${DEPLOY_TOOL}" = "1" ]; then
  export TOOL_MODEL=${TOOL_MODEL:-yapwithai/yap-longformer-screenshot-intent}
fi

if [ "${DEPLOY_CHAT}" = "1" ] || [ "${DEPLOY_TOOL}" = "1" ]; then
  log_info "AWQ models configured:"
  if [ "${DEPLOY_CHAT}" = "1" ]; then
    log_info "  Chat: ${CHAT_MODEL:-none}"
  fi
  if [ "${DEPLOY_TOOL}" = "1" ]; then
    log_info "  Tool: ${TOOL_MODEL:-none}"
  fi
  log_info "  Runtime quantization: Chat runs AWQ (W4A16); tool classifier stays float."
fi

# Validate models for enabled engines when QUANTIZATION=awq
if [ "${QUANTIZATION:-awq}" = "awq" ]; then
  if [ "${DEPLOY_CHAT}" = "1" ] && [ -z "${CHAT_MODEL:-}" ]; then
    log_error "Error: CHAT_MODEL must be set when deploying chat in AWQ mode"
    exit 1
  fi
fi

# Set quantization only for selected engines
if [ "${QUANTIZATION:-awq}" = "awq" ]; then
  if [ "${DEPLOY_CHAT}" = "1" ]; then
    export CHAT_QUANTIZATION=awq
  fi
fi


