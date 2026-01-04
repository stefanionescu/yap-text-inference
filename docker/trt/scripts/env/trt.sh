#!/usr/bin/env bash
# TensorRT-LLM engine configuration.
#
# Sets TRT engine paths and inference limits.

# Engine directory - where the compiled TRT engine is stored
export TRT_ENGINE_DIR=${TRT_ENGINE_DIR:-/opt/engines/trt-chat}

# Context and output limits
export CHAT_MAX_LEN=${CHAT_MAX_LEN:-5525}
export CHAT_MAX_OUT=${CHAT_MAX_OUT:-150}

# TRT-specific settings
export TRTLLM_MAX_INPUT_LEN=${TRTLLM_MAX_INPUT_LEN:-4096}
export TRTLLM_MAX_OUTPUT_LEN=${TRTLLM_MAX_OUTPUT_LEN:-512}
export TRTLLM_MAX_BATCH_SIZE=${TRTLLM_MAX_BATCH_SIZE:-16}

