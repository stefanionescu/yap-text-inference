#!/usr/bin/env bash

# Deployment selection: allow chat-only, tool-only, dual, or both (default both)
export DEPLOY_MODELS=${DEPLOY_MODELS:-both}
case "${DEPLOY_MODELS}" in
  both|chat|tool|dual) ;;
  *) log_warn "Invalid DEPLOY_MODELS='${DEPLOY_MODELS}', defaulting to 'both'"; export DEPLOY_MODELS=both;;
esac

# Convenience flags
DEPLOY_CHAT=0; DEPLOY_TOOL=0; DEPLOY_DUAL=0
if [ "${DEPLOY_MODELS}" = "both" ] || [ "${DEPLOY_MODELS}" = "chat" ] || [ "${DEPLOY_MODELS}" = "dual" ]; then DEPLOY_CHAT=1; fi
if [ "${DEPLOY_MODELS}" = "both" ] || [ "${DEPLOY_MODELS}" = "tool" ] || [ "${DEPLOY_MODELS}" = "dual" ]; then DEPLOY_TOOL=1; fi
if [ "${DEPLOY_MODELS}" = "dual" ]; then DEPLOY_DUAL=1; fi
export DEPLOY_CHAT DEPLOY_TOOL DEPLOY_DUAL

if [ "${DEPLOY_DUAL}" = "1" ]; then
  if [ -z "${DUAL_MODEL:-}" ]; then
    if [ -n "${CHAT_MODEL:-}" ]; then
      DUAL_MODEL="${CHAT_MODEL}"
    elif [ -n "${TOOL_MODEL:-}" ]; then
      DUAL_MODEL="${TOOL_MODEL}"
    fi
  fi
  export DUAL_MODEL
fi

# Only set defaults for the engines that are actually being deployed
if [ "${DEPLOY_CHAT}" = "1" ]; then
  export CHAT_MODEL=${CHAT_MODEL:-yapwithai/impish-12b-awq}
fi
if [ "${DEPLOY_DUAL}" = "1" ]; then
  export DUAL_MODEL="${DUAL_MODEL:-${CHAT_MODEL:-${TOOL_MODEL:-}}}"
fi
if [ "${DEPLOY_TOOL}" = "1" ]; then
  if [ "${DEPLOY_DUAL}" = "1" ]; then
    if [ -n "${DUAL_MODEL:-}" ]; then
      export TOOL_MODEL="${DUAL_MODEL}"
    else
      export TOOL_MODEL="${CHAT_MODEL:-yapwithai/impish-12b-awq}"
    fi
  else
    export TOOL_MODEL=${TOOL_MODEL:-yapwithai/hammer-2.1-3b-awq}
  fi
fi

if [ "${DEPLOY_CHAT}" = "1" ] || [ "${DEPLOY_TOOL}" = "1" ]; then
  log_info "AWQ models configured:"
  if [ "${DEPLOY_CHAT}" = "1" ]; then
    log_info "  Chat: ${CHAT_MODEL:-none}"
  fi
  if [ "${DEPLOY_TOOL}" = "1" ]; then
    if [ "${DEPLOY_DUAL}" = "1" ]; then
      log_info "  Tool (dual): ${TOOL_MODEL:-none}"
    else
      log_info "  Tool: ${TOOL_MODEL:-none}"
    fi
  fi
  log_info "  Runtime quantization: 4-bit W4A16 compressed tensors (llmcompressor exports autodetected by vLLM)"
fi

# Validate models for enabled engines when QUANTIZATION=awq
if [ "${QUANTIZATION:-awq}" = "awq" ]; then
  if [ "${DEPLOY_CHAT}" = "1" ] && [ -z "${CHAT_MODEL:-}" ]; then
    log_error "Error: CHAT_MODEL must be set when deploying chat in AWQ mode"
    exit 1
  fi
  if [ "${DEPLOY_TOOL}" = "1" ] && [ "${DEPLOY_DUAL}" != "1" ] && [ -z "${TOOL_MODEL:-}" ]; then
    log_error "Error: TOOL_MODEL must be set when deploying tool in AWQ mode"
    exit 1
  fi
fi

# Set quantization only for selected engines
if [ "${QUANTIZATION:-awq}" = "awq" ]; then
  if [ "${DEPLOY_CHAT}" = "1" ]; then
    export CHAT_QUANTIZATION=awq
  fi
  if [ "${DEPLOY_TOOL}" = "1" ]; then
    if [ "${DEPLOY_DUAL}" = "1" ]; then
      export TOOL_QUANTIZATION="${CHAT_QUANTIZATION:-awq}"
    else
      export TOOL_QUANTIZATION=awq
    fi
  fi
fi


