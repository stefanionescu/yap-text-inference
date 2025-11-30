#!/usr/bin/env bash

# Deploy mode and validation helpers

setup_deploy_mode_and_validate() {
  # Deploy mode: both | chat | tool | dual (default: both)
  export DEPLOY_MODELS=${DEPLOY_MODELS:-both}
  case "${DEPLOY_MODELS}" in
    both|chat|tool|dual)
      ;;
    *)
      log_warn "Invalid DEPLOY_MODELS='${DEPLOY_MODELS}', defaulting to 'both'"
      export DEPLOY_MODELS=both
      ;;
  esac

  # Convenience booleans for shell usage
  local deploy_chat=0
  local deploy_tool=0
  local deploy_dual=0
  if [ "${DEPLOY_MODELS}" = "both" ] || [ "${DEPLOY_MODELS}" = "chat" ] || [ "${DEPLOY_MODELS}" = "dual" ]; then
    deploy_chat=1
  fi
  if [ "${DEPLOY_MODELS}" = "both" ] || [ "${DEPLOY_MODELS}" = "tool" ] || [ "${DEPLOY_MODELS}" = "dual" ]; then
    deploy_tool=1
  fi
  if [ "${DEPLOY_MODELS}" = "dual" ]; then
    deploy_dual=1
  fi
  export DEPLOY_CHAT=${deploy_chat}
  export DEPLOY_TOOL=${deploy_tool}
  export DEPLOY_DUAL=${deploy_dual}

  if [ "${deploy_dual}" = "1" ]; then
    if [ -z "${DUAL_MODEL:-}" ]; then
      if [ -n "${CHAT_MODEL:-}" ]; then
        DUAL_MODEL="${CHAT_MODEL}"
      elif [ -n "${TOOL_MODEL:-}" ]; then
        DUAL_MODEL="${TOOL_MODEL}"
      fi
    fi
    if [ -z "${DUAL_MODEL:-}" ]; then
      log_warn "Error: DUAL_MODEL must be set when DEPLOY_MODELS='dual'"
      return 1
    fi
    CHAT_MODEL="${CHAT_MODEL:-${DUAL_MODEL}}"
    TOOL_MODEL="${TOOL_MODEL:-${DUAL_MODEL}}"
    export DUAL_MODEL CHAT_MODEL TOOL_MODEL
  else
    unset DUAL_MODEL
  fi

  # Validate required environment variables are set by main.sh (conditional on deploy mode)
  if [ "${DEPLOY_CHAT}" = "1" ] && [ -z "${CHAT_MODEL:-}" ]; then
    log_warn "Error: CHAT_MODEL must be set when DEPLOY_MODELS='both', 'chat', or 'dual'"
    return 1
  fi
  if [ "${DEPLOY_TOOL}" = "1" ] && [ "${deploy_dual}" != "1" ] && [ -z "${TOOL_MODEL:-}" ]; then
    log_warn "Error: TOOL_MODEL must be set when DEPLOY_MODELS='both' or 'tool'"
    return 1
  fi

  if [ -z "${QUANTIZATION:-}" ]; then
    log_warn "Error: QUANTIZATION environment variable must be set by main.sh"
    return 1
  fi
}


