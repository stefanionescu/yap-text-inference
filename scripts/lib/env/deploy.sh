#!/usr/bin/env bash
# =============================================================================
# Deploy Mode Configuration
# =============================================================================
# Validates and configures deploy modes (chat, tool, both) and ensures
# required models are specified for each deployment type.

setup_deploy_mode_and_validate() {
  # Deploy mode: both | chat | tool (default: both)
  export DEPLOY_MODE=${DEPLOY_MODE:-both}
  case "${DEPLOY_MODE}" in
    both|chat|tool)
      ;;
    *)
      log_warn "[env] ⚠ Invalid DEPLOY_MODE='${DEPLOY_MODE}', defaulting to 'both'"
      export DEPLOY_MODE=both
      ;;
  esac

  # Convenience booleans for shell usage
  local deploy_chat=0
  local deploy_tool=0
  if [ "${DEPLOY_MODE}" = "both" ] || [ "${DEPLOY_MODE}" = "chat" ]; then
    deploy_chat=1
  fi
  if [ "${DEPLOY_MODE}" = "both" ] || [ "${DEPLOY_MODE}" = "tool" ]; then
    deploy_tool=1
  fi
  export DEPLOY_CHAT=${deploy_chat}
  export DEPLOY_TOOL=${deploy_tool}

  # Validate required environment variables are set by main.sh (conditional on deploy mode)
  if [ "${DEPLOY_CHAT}" = "1" ] && [ -z "${CHAT_MODEL:-}" ]; then
    log_warn "[env] ⚠ CHAT_MODEL must be set when DEPLOY_MODE='both' or 'chat'"
    return 1
  fi
  if [ "${DEPLOY_TOOL}" = "1" ] && [ -z "${TOOL_MODEL:-}" ]; then
    log_warn "[env] ⚠ TOOL_MODEL must be set when DEPLOY_MODE='both' or 'tool'"
    return 1
  fi

  if [ "${DEPLOY_CHAT}" = "1" ] && [ -z "${CHAT_QUANTIZATION:-}" ]; then
    log_warn "[env] ⚠ CHAT_QUANTIZATION environment variable must be set by main.sh"
    return 1
  fi
}


