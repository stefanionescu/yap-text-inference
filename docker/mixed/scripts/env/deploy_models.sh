#!/usr/bin/env bash

# Deployment selection
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

# Only use preloaded models embedded into the image
PRELOADED_CHAT_DIR="/app/models/chat"
PRELOADED_TOOL_DIR="/app/models/tool"
PRELOADED_CHAT_AWQ_DIR="/app/models/chat_awq"
PRELOADED_TOOL_AWQ_DIR="/app/models/tool_awq"

# Determine if pre-quantized AWQ dirs exist
HAS_PRELOADED_AWQ_CHAT=0
HAS_PRELOADED_AWQ_TOOL=0
if [ -f "${PRELOADED_CHAT_AWQ_DIR}/.awq_ok" ] || [ -f "${PRELOADED_CHAT_AWQ_DIR}/awq_metadata.json" ] || [ -f "${PRELOADED_CHAT_AWQ_DIR}/awq_config.json" ]; then
  HAS_PRELOADED_AWQ_CHAT=1
fi
if [ -f "${PRELOADED_TOOL_AWQ_DIR}/.awq_ok" ] || [ -f "${PRELOADED_TOOL_AWQ_DIR}/awq_metadata.json" ] || [ -f "${PRELOADED_TOOL_AWQ_DIR}/awq_config.json" ]; then
  HAS_PRELOADED_AWQ_TOOL=1
fi

# Resolve model sources: preloaded AWQ -> preloaded float
if [ "${DEPLOY_CHAT}" = "1" ]; then
  if [ "${HAS_PRELOADED_AWQ_CHAT}" = "1" ]; then
    export CHAT_MODEL="${PRELOADED_CHAT_AWQ_DIR}"; export CHAT_QUANTIZATION=awq
  elif [ -d "${PRELOADED_CHAT_DIR}" ]; then
    export CHAT_MODEL="${PRELOADED_CHAT_DIR}"
  fi
fi

if [ "${DEPLOY_DUAL}" = "1" ]; then
  export DUAL_MODEL="${DUAL_MODEL:-${CHAT_MODEL:-${TOOL_MODEL:-}}}"
fi

if [ "${DEPLOY_TOOL}" = "1" ]; then
  if [ "${DEPLOY_DUAL}" = "1" ]; then
    if [ -n "${DUAL_MODEL:-}" ]; then
      export TOOL_MODEL="${DUAL_MODEL}"
    else
      export TOOL_MODEL="${CHAT_MODEL}"
    fi
    if [ -n "${CHAT_QUANTIZATION:-}" ]; then
      export TOOL_QUANTIZATION="${CHAT_QUANTIZATION}"
    fi
  else
    if [ "${HAS_PRELOADED_AWQ_TOOL}" = "1" ]; then
      export TOOL_MODEL="${PRELOADED_TOOL_AWQ_DIR}"; export TOOL_QUANTIZATION=awq
    elif [ -d "${PRELOADED_TOOL_DIR}" ]; then
      export TOOL_MODEL="${PRELOADED_TOOL_DIR}"
    fi
  fi
fi

# Guard required models
if [ "${DEPLOY_CHAT}" = "1" ] && [ -z "${CHAT_MODEL:-}" ]; then
  log_error "CHAT model not embedded in image; rebuild the image with a chat source"
  exit 1
fi
if [ "${DEPLOY_TOOL}" = "1" ] && [ "${DEPLOY_DUAL}" != "1" ] && [ -z "${TOOL_MODEL:-}" ]; then
  log_error "TOOL model not embedded in image; rebuild the image with a tool source"
  exit 1
fi


