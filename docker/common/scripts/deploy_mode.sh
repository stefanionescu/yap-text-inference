#!/usr/bin/env bash
# =============================================================================
# Shared Deploy Mode Configuration
# =============================================================================
# Common deploy mode handling used by both TRT and vLLM Docker images.
# Sets DEPLOY_MODE, DEPLOY_CHAT, and DEPLOY_TOOL flags.

# Validate and normalize DEPLOY_MODE
normalize_deploy_mode() {
  local log_prefix="${1:-[docker]}"

  export DEPLOY_MODE="${DEPLOY_MODE:-both}"
  case "${DEPLOY_MODE}" in
    both | chat | tool) ;;
    *)
      log_warn "${log_prefix} ⚠ Invalid DEPLOY_MODE='${DEPLOY_MODE}', defaulting to 'both'"
      export DEPLOY_MODE="both"
      ;;
  esac
}

# Set convenience flags based on DEPLOY_MODE
set_deploy_flags() {
  DEPLOY_CHAT=0
  DEPLOY_TOOL=0

  if [ "${DEPLOY_MODE}" = "both" ] || [ "${DEPLOY_MODE}" = "chat" ]; then
    DEPLOY_CHAT=1
  fi

  if [ "${DEPLOY_MODE}" = "both" ] || [ "${DEPLOY_MODE}" = "tool" ]; then
    DEPLOY_TOOL=1
  fi

  export DEPLOY_CHAT DEPLOY_TOOL
}

# Validate that required models are configured for the deploy mode
validate_deploy_models() {
  local log_prefix="${1:-[docker]}"
  local engine="${2:-vllm}"

  if [ "${DEPLOY_CHAT}" = "1" ] && [ -z "${CHAT_MODEL:-}" ]; then
    log_err "${log_prefix} ✗ CHAT_MODEL not configured in this image. This image was not built correctly."
    exit 1
  fi

  if [ "${DEPLOY_TOOL}" = "1" ] && [ -z "${TOOL_MODEL:-}" ]; then
    log_err "${log_prefix} ✗ TOOL_MODEL not configured in this image. This image was not built correctly."
    exit 1
  fi

  # TRT-specific: warn if engine repo not configured
  if [ "${engine}" = "trt" ] && [ "${DEPLOY_CHAT}" = "1" ] && [ -z "${TRT_ENGINE_REPO:-}" ]; then
    log_warn "${log_prefix} ⚠ TRT_ENGINE_REPO not configured - expecting engine to be mounted at TRT_ENGINE_DIR"
  fi
}

# Initialize deploy mode configuration
# Usage: init_deploy_mode "[prefix]" "engine"
init_deploy_mode() {
  local log_prefix="${1:-[docker]}"
  local engine="${2:-vllm}"

  normalize_deploy_mode "${log_prefix}"
  set_deploy_flags
  validate_deploy_models "${log_prefix}" "${engine}"
}
