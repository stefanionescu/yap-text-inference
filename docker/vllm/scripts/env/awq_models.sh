#!/usr/bin/env bash

# Deployment selection: set at build time via Dockerfile ARG/ENV
# DEPLOY_MODE, CHAT_MODEL, TOOL_MODEL are configured when the image is built
export DEPLOY_MODE=${DEPLOY_MODE:-both}
case "${DEPLOY_MODE}" in
  both|chat|tool) ;;
  *) log_warn "[vllm] ⚠ Invalid DEPLOY_MODE='${DEPLOY_MODE}', defaulting to 'both'"; export DEPLOY_MODE=both;;
esac

# Convenience flags
DEPLOY_CHAT=0; DEPLOY_TOOL=0
if [ "${DEPLOY_MODE}" = "both" ] || [ "${DEPLOY_MODE}" = "chat" ]; then DEPLOY_CHAT=1; fi
if [ "${DEPLOY_MODE}" = "both" ] || [ "${DEPLOY_MODE}" = "tool" ]; then DEPLOY_TOOL=1; fi
export DEPLOY_CHAT DEPLOY_TOOL

# Models are configured at build time - no defaults, image knows which models to use
# These ENV vars are set in the Dockerfile during build
if [ "${DEPLOY_CHAT}" = "1" ] && [ -z "${CHAT_MODEL:-}" ]; then
  log_error "[vllm] ✗ CHAT_MODEL not configured in this image. This image was not built correctly."
  exit 1
fi
if [ "${DEPLOY_TOOL}" = "1" ] && [ -z "${TOOL_MODEL:-}" ]; then
  log_error "[vllm] ✗ TOOL_MODEL not configured in this image. This image was not built correctly."
  exit 1
fi


# Set quantization for chat model
if [ "${QUANTIZATION:-awq}" = "awq" ]; then
  if [ "${DEPLOY_CHAT}" = "1" ]; then
    export CHAT_QUANTIZATION=awq
  fi
fi

