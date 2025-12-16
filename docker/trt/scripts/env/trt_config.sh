#!/usr/bin/env bash

# TensorRT-LLM engine configuration

# Engine directory - where the compiled TRT engine is stored
export TRT_ENGINE_DIR=${TRT_ENGINE_DIR:-/opt/engines/trt-chat}

# GPU memory fractions based on deployment mode
# Same allocation as vLLM: 70%/20% when both, 90% when single
if [ "${DEPLOY_MODELS:-both}" = "both" ]; then
    # Both models: Chat gets 70%, Tool gets 20%
    export TRT_KV_FREE_GPU_FRAC=${TRT_KV_FREE_GPU_FRAC:-0.70}
    export TOOL_GPU_FRAC=${TOOL_GPU_FRAC:-0.20}
else
    # Single model: gets 90%
    export TRT_KV_FREE_GPU_FRAC=${TRT_KV_FREE_GPU_FRAC:-0.90}
    export TOOL_GPU_FRAC=${TOOL_GPU_FRAC:-0.90}
fi

# KV cache settings
export TRT_KV_ENABLE_BLOCK_REUSE=${TRT_KV_ENABLE_BLOCK_REUSE:-1}

# Context and output limits
export CHAT_MAX_LEN=${CHAT_MAX_LEN:-5525}
export CHAT_MAX_OUT=${CHAT_MAX_OUT:-150}

# TRT-specific settings
export TRTLLM_MAX_INPUT_LEN=${TRTLLM_MAX_INPUT_LEN:-4096}
export TRTLLM_MAX_OUTPUT_LEN=${TRTLLM_MAX_OUTPUT_LEN:-512}
export TRTLLM_MAX_BATCH_SIZE=${TRTLLM_MAX_BATCH_SIZE:-16}

