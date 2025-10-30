#!/usr/bin/env bash

# Setup Hugging Face and related env for AWQ quantization steps

awq_setup_hf_env() {
  export HF_HOME="${HF_HOME:-${ROOT_DIR}/.hf}"
  export HUGGINGFACE_HUB_CACHE="${HUGGINGFACE_HUB_CACHE:-${HF_HOME}/hub}"
  if [ -f "/etc/ssl/certs/ca-certificates.crt" ]; then
    export REQUESTS_CA_BUNDLE="${REQUESTS_CA_BUNDLE:-/etc/ssl/certs/ca-certificates.crt}"
  fi
  export HF_HUB_DISABLE_TELEMETRY=1
  # Respect user override; default to disabled to avoid DNS issues with xet transfer endpoints
  export HF_HUB_ENABLE_HF_TRANSFER=${HF_HUB_ENABLE_HF_TRANSFER:-0}
}


