#!/usr/bin/env bash
# =============================================================================
# Deploy Mode Configuration
# =============================================================================
# Validates and configures deploy modes (chat, tool, both) and ensures
# required models are specified for each deployment type.

_ENV_DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../config/values/core.sh
source "${_ENV_DEPLOY_DIR}/../../config/values/core.sh"
# shellcheck source=../../config/patterns.sh
source "${_ENV_DEPLOY_DIR}/../../config/patterns.sh"

setup_deploy_mode_and_validate() {
  # Deploy mode: both | chat | tool (default: both)
  export DEPLOY_MODE="${DEPLOY_MODE:-${CFG_DEFAULT_DEPLOY_MODE}}"
  case "${DEPLOY_MODE}" in
    "${CFG_DEPLOY_MODE_BOTH}" | "${CFG_DEPLOY_MODE_CHAT}" | "${CFG_DEPLOY_MODE_TOOL}") ;;
    *)
      log_warn "[env] Invalid DEPLOY_MODE='${DEPLOY_MODE}', defaulting to '${CFG_DEFAULT_DEPLOY_MODE}'"
      export DEPLOY_MODE="${CFG_DEFAULT_DEPLOY_MODE}"
      ;;
  esac

  # Convenience booleans for shell usage
  local deploy_chat=0
  local deploy_tool=0
  if [ "${DEPLOY_MODE}" = "${CFG_DEPLOY_MODE_BOTH}" ] || [ "${DEPLOY_MODE}" = "${CFG_DEPLOY_MODE_CHAT}" ]; then
    deploy_chat=1
  fi
  if [ "${DEPLOY_MODE}" = "${CFG_DEPLOY_MODE_BOTH}" ] || [ "${DEPLOY_MODE}" = "${CFG_DEPLOY_MODE_TOOL}" ]; then
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
