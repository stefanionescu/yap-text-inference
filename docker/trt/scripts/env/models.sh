#!/usr/bin/env bash

# Deployment selection: set at build time via Dockerfile ARG/ENV
# DEPLOY_MODE, CHAT_MODEL, TOOL_MODEL are configured when the image is built
export DEPLOY_MODE=${DEPLOY_MODE:-both}
case "${DEPLOY_MODE}" in
  both|chat|tool) ;;
  *) log_warn "[trt] ⚠ Invalid DEPLOY_MODE='${DEPLOY_MODE}', defaulting to 'both'"; export DEPLOY_MODE=both;;
esac

# Convenience flags
DEPLOY_CHAT=0; DEPLOY_TOOL=0
if [ "${DEPLOY_MODE}" = "both" ] || [ "${DEPLOY_MODE}" = "chat" ]; then DEPLOY_CHAT=1; fi
if [ "${DEPLOY_MODE}" = "both" ] || [ "${DEPLOY_MODE}" = "tool" ]; then DEPLOY_TOOL=1; fi
export DEPLOY_CHAT DEPLOY_TOOL

# Models are configured at build time - no defaults, image knows which models to use
# For TRT: CHAT_MODEL is used for the tokenizer, TRT_ENGINE_REPO provides the engine
if [ "${DEPLOY_CHAT}" = "1" ] && [ -z "${CHAT_MODEL:-}" ]; then
  log_error "[trt] ✗ CHAT_MODEL not configured in this image. This image was not built correctly."
  exit 1
fi
if [ "${DEPLOY_CHAT}" = "1" ] && [ -z "${TRT_ENGINE_REPO:-}" ]; then
  # TRT_ENGINE_REPO can be empty if user is mounting the engine directory
  log_warn "[trt] ⚠ TRT_ENGINE_REPO not configured - expecting engine to be mounted at TRT_ENGINE_DIR"
fi
if [ "${DEPLOY_TOOL}" = "1" ] && [ -z "${TOOL_MODEL:-}" ]; then
  log_error "[trt] ✗ TOOL_MODEL not configured in this image. This image was not built correctly."
  exit 1
fi

if [ "${DEPLOY_CHAT}" = "1" ] || [ "${DEPLOY_TOOL}" = "1" ]; then
  log_info "[trt] Configured models:"
  if [ "${DEPLOY_CHAT}" = "1" ]; then
    log_info "[trt]   Chat (tokenizer): ${CHAT_MODEL}"
    log_info "[trt]   TRT engine repo: ${TRT_ENGINE_REPO:-<mount required>}"
  fi
  if [ "${DEPLOY_TOOL}" = "1" ]; then
    log_info "[trt]   Tool classifier: ${TOOL_MODEL}"
  fi
fi

