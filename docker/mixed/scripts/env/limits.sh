#!/usr/bin/env bash

# Context and output limits
export CHAT_MAX_LEN=${CHAT_MAX_LEN:-5160}
export CHAT_MAX_OUT=${CHAT_MAX_OUT:-150}
export TOOL_MAX_OUT=${TOOL_MAX_OUT:-10}
export TOOL_MAX_LEN=${TOOL_MAX_LEN:-3000}

# GPU memory allocation
if [ "${DEPLOY_MODELS}" = "both" ]; then
  export CHAT_GPU_FRAC=${CHAT_GPU_FRAC:-0.71}
  export TOOL_GPU_FRAC=${TOOL_GPU_FRAC:-0.21}
else
  export CHAT_GPU_FRAC=${CHAT_GPU_FRAC:-0.92}
  export TOOL_GPU_FRAC=${TOOL_GPU_FRAC:-0.92}
fi

# vLLM toggles
export VLLM_USE_V1=${VLLM_USE_V1:-1}
export ENFORCE_EAGER=${ENFORCE_EAGER:-0}
export VLLM_ALLOW_LONG_MAX_MODEL_LEN=${VLLM_ALLOW_LONG_MAX_MODEL_LEN:-1}


