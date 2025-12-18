#!/usr/bin/env bash

# Deploy mode and validation helpers

setup_deploy_mode_and_validate() {
  # Deploy mode: both | chat | tool (default: both)
  export DEPLOY_MODELS=${DEPLOY_MODELS:-both}
  case "${DEPLOY_MODELS}" in
    both|chat|tool)
      ;;
    *)
      log_warn "[env] Invalid DEPLOY_MODELS='${DEPLOY_MODELS}', defaulting to 'both'"
      export DEPLOY_MODELS=both
      ;;
  esac

  # Convenience booleans for shell usage
  local deploy_chat=0
  local deploy_tool=0
  if [ "${DEPLOY_MODELS}" = "both" ] || [ "${DEPLOY_MODELS}" = "chat" ]; then
    deploy_chat=1
  fi
  if [ "${DEPLOY_MODELS}" = "both" ] || [ "${DEPLOY_MODELS}" = "tool" ]; then
    deploy_tool=1
  fi
  export DEPLOY_CHAT=${deploy_chat}
  export DEPLOY_TOOL=${deploy_tool}

  # Validate required environment variables are set by main.sh (conditional on deploy mode)
  if [ "${DEPLOY_CHAT}" = "1" ] && [ -z "${CHAT_MODEL:-}" ]; then
    log_warn "[env] CHAT_MODEL must be set when DEPLOY_MODELS='both' or 'chat'"
    return 1
  fi
  if [ "${DEPLOY_TOOL}" = "1" ] && [ -z "${TOOL_MODEL:-}" ]; then
    log_warn "[env] TOOL_MODEL must be set when DEPLOY_MODELS='both' or 'tool'"
    return 1
  fi

  if [ "${DEPLOY_CHAT}" = "1" ] && [ -z "${QUANTIZATION:-}" ]; then
    log_warn "[env] QUANTIZATION environment variable must be set by main.sh"
    return 1
  fi
}


