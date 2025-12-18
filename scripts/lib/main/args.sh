#!/usr/bin/env bash
# Argument parsing for main.sh
#
# Exports:
#   ENGINE_TYPE       - 'trt' or 'vllm'
#   PUSH_QUANT        - 0 or 1
#   QUANT_TYPE        - '4bit', '8bit', or 'auto'
#   CHAT_MODEL_NAME   - Chat model path/name
#   TOOL_MODEL_NAME   - Tool model path/name
#   DEPLOY_MODE_SELECTED - 'both', 'chat', or 'tool'

# Parse engine and push flags from arguments
# Usage: main_parse_flags "$@"
# Sets: ENGINE_TYPE, PUSH_QUANT, and remaining args via MAIN_REMAINING_ARGS
main_parse_flags() {
  PUSH_QUANT=0
  ENGINE_TYPE="${INFERENCE_ENGINE:-trt}"
  MAIN_REMAINING_ARGS=()

  while [ $# -gt 0 ]; do
    case "$1" in
      --push-quant)
        PUSH_QUANT=1
        shift
        ;;
      --no-push-quant)
        PUSH_QUANT=0
        shift
        ;;
      --engine=*)
        ENGINE_TYPE="${1#--engine=}"
        shift
        ;;
      --vllm)
        ENGINE_TYPE="vllm"
        shift
        ;;
      --trt|--tensorrt)
        ENGINE_TYPE="trt"
        shift
        ;;
      *)
        MAIN_REMAINING_ARGS+=("$1")
        shift
        ;;
    esac
  done

  # Normalize engine type
  case "${ENGINE_TYPE}" in
    vllm|VLLM)
      ENGINE_TYPE="vllm"
      ;;
    trt|TRT|tensorrt|TENSORRT|trtllm|TRTLLM)
      ENGINE_TYPE="trt"
      ;;
    *)
      log_warn "[main] Unknown engine type '${ENGINE_TYPE}', defaulting to 'trt'"
      ENGINE_TYPE="trt"
      ;;
  esac

  export ENGINE_TYPE PUSH_QUANT
  export HF_AWQ_PUSH="${PUSH_QUANT}"
  export INFERENCE_ENGINE="${ENGINE_TYPE}"
}

# Parse quantization type from first argument
# Usage: main_parse_quant_type "$@"
# Sets: QUANT_TYPE, updates MAIN_REMAINING_ARGS
main_parse_quant_type() {
  QUANT_TYPE="auto"
  
  case "${1:-}" in
    4bit|4BIT|4Bit)
      QUANT_TYPE="4bit"
      shift
      ;;
    8bit|8BIT|8Bit)
      QUANT_TYPE="8bit"
      shift
      ;;
    awq)
      log_warn "[main] Deprecated 'awq' flag detected; use '4bit' instead."
      QUANT_TYPE="4bit"
      shift
      ;;
    fp8)
      log_warn "[main] Deprecated 'fp8' flag detected; use '8bit' instead."
      QUANT_TYPE="8bit"
      shift
      ;;
  esac

  # Update remaining args
  MAIN_REMAINING_ARGS=("$@")
  export QUANT_TYPE
}

# Parse deploy mode and model names from remaining arguments
# Usage: main_parse_models
# Reads from: MAIN_REMAINING_ARGS
# Sets: CHAT_MODEL_NAME, TOOL_MODEL_NAME, DEPLOY_MODE_SELECTED
main_parse_models() {
  local args=("${MAIN_REMAINING_ARGS[@]}")
  
  # Initialize defaults
  CHAT_MODEL_NAME=""
  TOOL_MODEL_NAME=""
  DEPLOY_MODE_SELECTED="${DEPLOY_MODELS:-both}"
  
  # Validate initial deploy mode
  case "${DEPLOY_MODE_SELECTED}" in
    both|chat|tool) ;;
    *)
      log_warn "[main] Invalid DEPLOY_MODELS='${DEPLOY_MODE_SELECTED}', defaulting to 'both'"
      DEPLOY_MODE_SELECTED="both"
      ;;
  esac

  # Check if first arg is a deploy mode keyword
  case "${args[0]:-}" in
    chat|tool|both)
      DEPLOY_MODE_SELECTED="${args[0]}"
      args=("${args[@]:1}")
      ;;
  esac

  # Parse models based on deploy mode
  case "${DEPLOY_MODE_SELECTED}" in
    chat)
      if [ ${#args[@]} -lt 1 ]; then
        log_warn "[main] chat-only mode requires <chat_model>"
        return 1
      fi
      CHAT_MODEL_NAME="${args[0]}"
      args=("${args[@]:1}")
      ;;
    tool)
      if [ ${#args[@]} -lt 1 ]; then
        log_warn "[main] tool-only mode requires <tool_model>"
        return 1
      fi
      TOOL_MODEL_NAME="${args[0]}"
      args=("${args[@]:1}")
      ;;
    both)
      if [ ${#args[@]} -lt 2 ]; then
        log_warn "[main] both mode requires <chat_model> <tool_model>"
        return 1
      fi
      CHAT_MODEL_NAME="${args[0]}"
      TOOL_MODEL_NAME="${args[1]}"
      args=("${args[@]:2}")
      ;;
  esac

  # Validate required models
  if [ "${DEPLOY_MODE_SELECTED}" != "tool" ] && [ -z "${CHAT_MODEL_NAME}" ]; then
    log_warn "[main] CHAT_MODEL is required for deploy mode '${DEPLOY_MODE_SELECTED}'"
    return 1
  fi
  if [ "${DEPLOY_MODE_SELECTED}" != "chat" ] && [ -z "${TOOL_MODEL_NAME}" ]; then
    log_warn "[main] TOOL_MODEL is required for deploy mode '${DEPLOY_MODE_SELECTED}'"
    return 1
  fi

  # Check for trailing deploy mode override
  if [ ${#args[@]} -gt 0 ]; then
    case "${args[0]}" in
      chat|tool|both)
        DEPLOY_MODE_SELECTED="${args[0]}"
        ;;
    esac
  fi

  # Final normalization
  case "${DEPLOY_MODE_SELECTED:-both}" in
    both|chat|tool)
      export DEPLOY_MODELS="${DEPLOY_MODE_SELECTED:-both}"
      ;;
    *)
      log_warn "[main] Invalid deploy_mode '${DEPLOY_MODE_SELECTED}', defaulting to 'both'"
      export DEPLOY_MODELS=both
      ;;
  esac

  export CHAT_MODEL_NAME TOOL_MODEL_NAME DEPLOY_MODE_SELECTED
  return 0
}

# Export models to environment variables
main_export_models() {
  if [ "${DEPLOY_MODELS}" = "both" ] || [ "${DEPLOY_MODELS}" = "chat" ]; then
    export CHAT_MODEL="${CHAT_MODEL_NAME}"
  fi
  if [ "${DEPLOY_MODELS}" = "both" ] || [ "${DEPLOY_MODELS}" = "tool" ]; then
    export TOOL_MODEL="${TOOL_MODEL_NAME}"
  fi
}

