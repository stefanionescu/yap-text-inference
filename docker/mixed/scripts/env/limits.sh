#!/usr/bin/env bash

# Context and output limits
export CHAT_MAX_LEN=${CHAT_MAX_LEN:-5025}
export CHAT_MAX_OUT=${CHAT_MAX_OUT:-150}

# GPU memory allocation
if [ "${DEPLOY_MODELS:-both}" = "both" ]; then
  export CHAT_GPU_FRAC=${CHAT_GPU_FRAC:-0.70}
  export TOOL_GPU_FRAC=${TOOL_GPU_FRAC:-0.20}
else
  export CHAT_GPU_FRAC=${CHAT_GPU_FRAC:-0.90}
  export TOOL_GPU_FRAC=${TOOL_GPU_FRAC:-0.90}
fi

# vLLM toggles
export VLLM_USE_V1=${VLLM_USE_V1:-1}
export ENFORCE_EAGER=${ENFORCE_EAGER:-0}
export VLLM_ALLOW_LONG_MAX_MODEL_LEN=${VLLM_ALLOW_LONG_MAX_MODEL_LEN:-1}

# Prefill batching overrides
export MAX_NUM_SEQS_CHAT=${MAX_NUM_SEQS_CHAT:-32}


