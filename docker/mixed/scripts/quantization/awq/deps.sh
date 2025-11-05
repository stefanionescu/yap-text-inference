#!/usr/bin/env bash

# Hugging Face environment setup for AWQ
export HF_HOME="${HF_HOME:-${ROOT_DIR}/.hf}"
export HUGGINGFACE_HUB_CACHE="${HUGGINGFACE_HUB_CACHE:-${HF_HOME}/hub}"
if [ -f "/etc/ssl/certs/ca-certificates.crt" ]; then
  export REQUESTS_CA_BUNDLE="${REQUESTS_CA_BUNDLE:-/etc/ssl/certs/ca-certificates.crt}"
fi

export HF_HUB_DISABLE_TELEMETRY=1
export HF_HUB_ENABLE_HF_TRANSFER=${HF_HUB_ENABLE_HF_TRANSFER:-0}
