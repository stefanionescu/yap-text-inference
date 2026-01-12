#!/usr/bin/env bash
# TensorRT-LLM engine configuration.
#
# Sets TRT engine paths and inference limits.
# All variables use TRT_* naming to match Python config.

# Engine directory - where the compiled TRT engine is stored
export TRT_ENGINE_DIR=${TRT_ENGINE_DIR:-/opt/engines/trt-chat}

# Context and output limits
export CHAT_MAX_LEN=${CHAT_MAX_LEN:-5025}
export CHAT_MAX_OUT=${CHAT_MAX_OUT:-150}

# TRT-specific settings (aligned with Python src/config/trt.py)
export TRT_MAX_INPUT_LEN=${TRT_MAX_INPUT_LEN:-${CHAT_MAX_LEN}}
export TRT_MAX_OUTPUT_LEN=${TRT_MAX_OUTPUT_LEN:-${CHAT_MAX_OUT}}
export TRT_MAX_BATCH_SIZE=${TRT_MAX_BATCH_SIZE:-16}

