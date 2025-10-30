#!/usr/bin/env bash

# Deployment selection
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

# Check for models provided by the user
CHAT_MODEL_IN=${CHAT_MODEL:-}
TOOL_MODEL_IN=${TOOL_MODEL:-}
AWQ_CHAT_MODEL_IN=${AWQ_CHAT_MODEL:-}
AWQ_TOOL_MODEL_IN=${AWQ_TOOL_MODEL:-}

# Enforce exactly one source per engine
if [ -n "${AWQ_CHAT_MODEL_IN}" ] && [ -n "${CHAT_MODEL_IN}" ]; then
  log_error "Specify only one chat model source: either AWQ_CHAT_MODEL or CHAT_MODEL (not both)"
  exit 1
fi
if [ -n "${AWQ_TOOL_MODEL_IN}" ] && [ -n "${TOOL_MODEL_IN}" ]; then
  log_error "Specify only one tool model source: either AWQ_TOOL_MODEL or TOOL_MODEL (not both)"
  exit 1
fi

# Prefer preloaded models if env not given
PRELOADED_CHAT_DIR="/app/models/chat"
PRELOADED_TOOL_DIR="/app/models/tool"
PRELOADED_CHAT_AWQ_DIR="/app/models/chat_awq"
PRELOADED_TOOL_AWQ_DIR="/app/models/tool_awq"

# Determine if pre-quantized AWQ dirs exist
HAS_PRELOADED_AWQ_CHAT=0
HAS_PRELOADED_AWQ_TOOL=0
if [ -f "${PRELOADED_CHAT_AWQ_DIR}/awq_config.json" ] || [ -f "${PRELOADED_CHAT_AWQ_DIR}/.awq_ok" ]; then
  HAS_PRELOADED_AWQ_CHAT=1
fi
if [ -f "${PRELOADED_TOOL_AWQ_DIR}/awq_config.json" ] || [ -f "${PRELOADED_TOOL_AWQ_DIR}/.awq_ok" ]; then
  HAS_PRELOADED_AWQ_TOOL=1
fi

# Resolve model sources in priority order: explicit env -> preloaded AWQ -> preloaded float/GPTQ
if [ "${DEPLOY_CHAT}" = "1" ]; then
  if [ -n "${AWQ_CHAT_MODEL_IN}" ]; then
    export CHAT_MODEL="${AWQ_CHAT_MODEL_IN}"; export CHAT_QUANTIZATION=awq
  elif [ "${HAS_PRELOADED_AWQ_CHAT}" = "1" ]; then
    export CHAT_MODEL="${PRELOADED_CHAT_AWQ_DIR}"; export CHAT_QUANTIZATION=awq
  elif [ -n "${CHAT_MODEL_IN}" ]; then
    export CHAT_MODEL="${CHAT_MODEL_IN}"
  elif [ -d "${PRELOADED_CHAT_DIR}" ]; then
    export CHAT_MODEL="${PRELOADED_CHAT_DIR}"
  fi
fi

if [ "${DEPLOY_TOOL}" = "1" ]; then
  if [ -n "${AWQ_TOOL_MODEL_IN}" ]; then
    export TOOL_MODEL="${AWQ_TOOL_MODEL_IN}"; export TOOL_QUANTIZATION=awq
  elif [ "${HAS_PRELOADED_AWQ_TOOL}" = "1" ]; then
    export TOOL_MODEL="${PRELOADED_TOOL_AWQ_DIR}"; export TOOL_QUANTIZATION=awq
  elif [ -n "${TOOL_MODEL_IN}" ]; then
    export TOOL_MODEL="${TOOL_MODEL_IN}"
  elif [ -d "${PRELOADED_TOOL_DIR}" ]; then
    export TOOL_MODEL="${PRELOADED_TOOL_DIR}"
  fi
fi

# Guard required models
if [ "${DEPLOY_CHAT}" = "1" ] && [ -z "${CHAT_MODEL:-}" ]; then
  log_error "CHAT_MODEL must be specified (env or preloaded) when deploying chat"
  exit 1
fi
if [ "${DEPLOY_TOOL}" = "1" ] && [ -z "${TOOL_MODEL:-}" ]; then
  log_error "TOOL_MODEL must be specified (env or preloaded) when deploying tool"
  exit 1
fi


