#!/usr/bin/env bash
# shellcheck disable=SC2034  # Variables are used by sourcing scripts.
# =============================================================================
# Common Argument Parsing Helpers
# =============================================================================
# Shared argument parsing utilities for main.sh and restart.sh. Provides
# unified parsing for logging flags, push flags, and engine selection.

_COMMON_ARGS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../config/values/core.sh
source "${_COMMON_ARGS_DIR}/../../config/values/core.sh"
# shellcheck source=../../config/patterns.sh
source "${_COMMON_ARGS_DIR}/../../config/patterns.sh"

# Initialize common argument state variables.
# Call this before parsing to set up defaults.
# Engine defaults are applied by mode-specific parsers (chat/both only).
init_common_state() {
  SHOW_HF_LOGS="${SHOW_HF_LOGS:-0}"
  SHOW_TRT_LOGS="${SHOW_TRT_LOGS:-0}"
  SHOW_VLLM_LOGS="${SHOW_VLLM_LOGS:-0}"
  SHOW_LLMCOMPRESSOR_LOGS="${SHOW_LLMCOMPRESSOR_LOGS:-0}"
  SHOW_TOOL_LOGS="${SHOW_TOOL_LOGS:-0}"
  HF_AWQ_PUSH_REQUESTED="${HF_AWQ_PUSH_REQUESTED:-0}"
  HF_AWQ_PUSH=0
  HF_ENGINE_PUSH_REQUESTED="${HF_ENGINE_PUSH_REQUESTED:-0}"
  HF_ENGINE_PUSH=0
  # Engine selection is mode-aware and applied after deploy mode resolution.
  INFERENCE_ENGINE="${INFERENCE_ENGINE:-}"
}

# Validate that mutually exclusive flags are not both set.
# Returns 0 if valid, 1 if invalid (with error message).
validate_common_state() {
  # --push-quant and --push-engine are mutually exclusive
  if [ "${HF_AWQ_PUSH_REQUESTED:-0}" = "1" ] && [ "${HF_ENGINE_PUSH_REQUESTED:-0}" = "1" ]; then
    log_err "[args] ✗ --push-quant and --push-engine are mutually exclusive."
    log_blank
    log_err "[args]   --push-quant: Upload freshly quantized model to a new/existing HF repo"
    log_err "[args]   --push-engine: Add locally-built engine to an existing prequantized HF repo"
    log_blank
    log_err "[args]   Choose one based on your use case."
    return 1
  fi
  return 0
}

# Export all common argument state variables.
export_common_state() {
  export SHOW_HF_LOGS SHOW_TRT_LOGS SHOW_VLLM_LOGS SHOW_LLMCOMPRESSOR_LOGS SHOW_TOOL_LOGS
  export HF_AWQ_PUSH HF_AWQ_PUSH_REQUESTED
  export HF_ENGINE_PUSH HF_ENGINE_PUSH_REQUESTED
  if [ -n "${INFERENCE_ENGINE:-}" ]; then
    export INFERENCE_ENGINE
  else
    unset INFERENCE_ENGINE 2>/dev/null || true
  fi
}

# Parse common non-engine flags. Returns 0 and sets ARGS_SHIFT_COUNT if handled.
# Returns 1 if the flag is not handled.
# Usage: if parse_common_non_engine_flag "$1" "$2"; then shift $ARGS_SHIFT_COUNT; fi
parse_common_non_engine_flag() {
  local flag="$1"
  ARGS_SHIFT_COUNT=1 # default; may be updated below

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
    --show-tool-logs)
      SHOW_TOOL_LOGS=1
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
  esac

  return 1
}

# Parse engine flags without applying them. The caller decides when to apply.
# Returns:
#   0 if handled (sets ARGS_SHIFT_COUNT, ENGINE_FLAG_NAME, ENGINE_FLAG_VALUE)
#   1 if not an engine flag
#   2 if invalid engine flag usage (e.g., --engine missing value)
parse_engine_flag_token() {
  local flag="$1"
  local next_arg="${2:-}"

  ARGS_SHIFT_COUNT=1
  ENGINE_FLAG_NAME=""
  ENGINE_FLAG_VALUE=""

  case "${flag}" in
    --trt)
      ENGINE_FLAG_NAME="--trt"
      ENGINE_FLAG_VALUE="${CFG_ENGINE_TRT}"
      return 0
      ;;
    --tensorrt)
      ENGINE_FLAG_NAME="--tensorrt"
      ENGINE_FLAG_VALUE="${CFG_ENGINE_TRT}"
      return 0
      ;;
    --vllm)
      ENGINE_FLAG_NAME="--vllm"
      ENGINE_FLAG_VALUE="${CFG_ENGINE_VLLM}"
      return 0
      ;;
    --engine)
      if [ -z "${next_arg}" ]; then
        return 2
      fi
      ENGINE_FLAG_NAME="--engine"
      ENGINE_FLAG_VALUE="${next_arg}"
      ARGS_SHIFT_COUNT=2
      return 0
      ;;
    --engine=*)
      ENGINE_FLAG_NAME="--engine"
      ENGINE_FLAG_VALUE="${flag#--engine=}"
      return 0
      ;;
  esac

  return 1
}

# Apply a sequence of deferred engine flags in order.
# Usage: apply_deferred_engine_flags <context> <flag_array...>
apply_deferred_engine_flags() {
  local context="$1"
  shift
  local -a deferred_flags=("$@")

  # Default engine for chat/both deployments.
  INFERENCE_ENGINE="${INFERENCE_ENGINE:-${CFG_DEFAULT_ENGINE}}"

  local idx=0
  local total=${#deferred_flags[@]}
  while [ "${idx}" -lt "${total}" ]; do
    local flag="${deferred_flags[$idx]}"
    case "${flag}" in
      --trt | --tensorrt)
        INFERENCE_ENGINE="${CFG_ENGINE_TRT}"
        ;;
      --vllm)
        INFERENCE_ENGINE="${CFG_ENGINE_VLLM}"
        ;;
      --engine)
        idx=$((idx + 1))
        if [ "${idx}" -ge "${total}" ]; then
          log_err "${context} ✗ --engine requires a value (trt|vllm)"
          return 1
        fi
        INFERENCE_ENGINE="${deferred_flags[$idx]}"
        ;;
      *)
        log_err "${context} ✗ Unknown deferred engine flag '${flag}'"
        return 1
        ;;
    esac
    idx=$((idx + 1))
  done

  if ! INFERENCE_ENGINE="$(cli_normalize_engine "${INFERENCE_ENGINE}")"; then
    log_err "${context} ✗ Unknown engine '${INFERENCE_ENGINE:-}'. Expected trt|vllm."
    return 1
  fi
  return 0
}

# Build an array of common flags for forwarding to another script.
# Populates the ARGS_FORWARD_FLAGS array.
build_forward_flags() {
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
  if [ "${SHOW_TOOL_LOGS:-0}" = "1" ]; then
    ARGS_FORWARD_FLAGS+=("--show-tool-logs")
  fi
  if [ "${HF_AWQ_PUSH_REQUESTED:-0}" = "1" ]; then
    ARGS_FORWARD_FLAGS+=("--push-quant")
  fi
  if [ "${HF_ENGINE_PUSH_REQUESTED:-0}" = "1" ]; then
    ARGS_FORWARD_FLAGS+=("--push-engine")
  fi
}
