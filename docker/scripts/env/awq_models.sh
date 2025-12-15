#!/usr/bin/env bash

# Deployment selection: set at build time via Dockerfile ARG/ENV
# DEPLOY_MODELS, CHAT_MODEL, TOOL_MODEL are configured when the image is built
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

# Models are configured at build time - no defaults, image knows which models to use
# These ENV vars are set in the Dockerfile during build
if [ "${DEPLOY_CHAT}" = "1" ] && [ -z "${CHAT_MODEL:-}" ]; then
  log_error "CHAT_MODEL not configured in this image. This image was not built correctly."
  exit 1
fi
if [ "${DEPLOY_TOOL}" = "1" ] && [ -z "${TOOL_MODEL:-}" ]; then
  log_error "TOOL_MODEL not configured in this image. This image was not built correctly."
  exit 1
fi

if [ "${DEPLOY_CHAT}" = "1" ] || [ "${DEPLOY_TOOL}" = "1" ]; then
  log_info "Configured models (will be downloaded from HuggingFace on first run):"
  if [ "${DEPLOY_CHAT}" = "1" ]; then
    log_info "  Chat: ${CHAT_MODEL}"
  fi
  if [ "${DEPLOY_TOOL}" = "1" ]; then
    log_info "  Tool: ${TOOL_MODEL}"
  fi
  log_info "  Runtime quantization: Chat runs AWQ (W4A16); tool classifier stays float."
fi

# Set quantization for chat model
if [ "${QUANTIZATION:-awq}" = "awq" ]; then
  if [ "${DEPLOY_CHAT}" = "1" ]; then
    export CHAT_QUANTIZATION=awq
  fi
fi
