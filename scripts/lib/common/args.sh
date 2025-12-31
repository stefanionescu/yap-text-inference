#!/usr/bin/env bash
# shellcheck disable=SC2034  # Variables are used by sourcing scripts.

# Common argument parsing helpers shared by main.sh and restart.sh.
# Provides unified parsing for logging flags, push flags, and engine selection.

# Initialize common argument state variables.
# Call this before parsing to set up defaults.
args_init_common_state() {
  SHOW_HF_LOGS="${SHOW_HF_LOGS:-0}"
  SHOW_TRT_LOGS="${SHOW_TRT_LOGS:-0}"
  SHOW_VLLM_LOGS="${SHOW_VLLM_LOGS:-0}"
  SHOW_LLMCOMPRESSOR_LOGS="${SHOW_LLMCOMPRESSOR_LOGS:-0}"
  HF_AWQ_PUSH_REQUESTED="${HF_AWQ_PUSH_REQUESTED:-0}"
  HF_AWQ_PUSH=0
  HF_ENGINE_PUSH_REQUESTED="${HF_ENGINE_PUSH_REQUESTED:-0}"
  HF_ENGINE_PUSH=0
  INFERENCE_ENGINE="${INFERENCE_ENGINE:-trt}"
}

# Export all common argument state variables.
args_export_common_state() {
  export SHOW_HF_LOGS SHOW_TRT_LOGS SHOW_VLLM_LOGS SHOW_LLMCOMPRESSOR_LOGS
  export HF_AWQ_PUSH HF_AWQ_PUSH_REQUESTED
  export HF_ENGINE_PUSH HF_ENGINE_PUSH_REQUESTED
  export INFERENCE_ENGINE
}

# Try to parse a common flag. Returns 0 and sets ARGS_SHIFT_COUNT if handled.
# Returns 1 if the flag is not a common flag.
# Usage: if args_parse_common_flag "$1" "$2"; then shift $ARGS_SHIFT_COUNT; fi
args_parse_common_flag() {
  local flag="$1"
  local next_arg="${2:-}"
  ARGS_SHIFT_COUNT=1  # default; may be updated below

  case "${flag}" in
    --show-hf-logs)
      SHOW_HF_LOGS=1
      return 0
      ;;
    --show-trt-logs)
      SHOW_TRT_LOGS=1
      return 0
      ;;
    --show-vllm-logs)
      SHOW_VLLM_LOGS=1
      return 0
      ;;
    --show-llmcompressor-logs)
      SHOW_LLMCOMPRESSOR_LOGS=1
      return 0
      ;;
    --push-quant)
      HF_AWQ_PUSH_REQUESTED=1
      return 0
      ;;
    --push-engine)
      HF_ENGINE_PUSH_REQUESTED=1
      return 0
      ;;
    --trt)
      INFERENCE_ENGINE="trt"
      return 0
      ;;
    --vllm)
      INFERENCE_ENGINE="vllm"
      return 0
      ;;
    --engine)
      if [ -z "${next_arg}" ]; then
        return 1
      fi
      INFERENCE_ENGINE="${next_arg}"
      ARGS_SHIFT_COUNT=2
      return 0
      ;;
    --engine=*)
      INFERENCE_ENGINE="${flag#--engine=}"
      return 0
      ;;
  esac

  return 1
}

# Build an array of common flags for forwarding to another script.
# Populates the ARGS_FORWARD_FLAGS array.
args_build_forward_flags() {
  ARGS_FORWARD_FLAGS=()

  if [ "${SHOW_HF_LOGS:-0}" = "1" ]; then
    ARGS_FORWARD_FLAGS+=("--show-hf-logs")
  fi
  if [ "${SHOW_TRT_LOGS:-0}" = "1" ]; then
    ARGS_FORWARD_FLAGS+=("--show-trt-logs")
  fi
  if [ "${SHOW_VLLM_LOGS:-0}" = "1" ]; then
    ARGS_FORWARD_FLAGS+=("--show-vllm-logs")
  fi
  if [ "${SHOW_LLMCOMPRESSOR_LOGS:-0}" = "1" ]; then
    ARGS_FORWARD_FLAGS+=("--show-llmcompressor-logs")
  fi
  if [ "${HF_AWQ_PUSH_REQUESTED:-0}" = "1" ]; then
    ARGS_FORWARD_FLAGS+=("--push-quant")
  fi
  if [ "${HF_ENGINE_PUSH_REQUESTED:-0}" = "1" ]; then
    ARGS_FORWARD_FLAGS+=("--push-engine")
  fi
}

