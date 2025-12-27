#!/usr/bin/env bash
# Argument parsing for main.sh
#
# main_parse_cli performs a single-pass parse that understands every supported
# switch, quantization shorthand, and deploy-mode override. Parsed values are
# exported so downstream scripts do not need to re-process argv.

main_parse_cli() {
  local engine="${INFERENCE_ENGINE:-trt}"
  local push_quant_requested="${HF_AWQ_PUSH:-0}"
  local quant_type="auto"
  local deploy_mode="${DEPLOY_MODE:-both}"
  local deploy_explicit=0
  local -a positional_args=()

  while [ $# -gt 0 ]; do
    case "$1" in
      -h|--help)
        main_usage
        return 1
        ;;
      --push-quant)
        push_quant_requested=1
        ;;
      --no-push-quant)
        push_quant_requested=0
        ;;
      --engine)
        if [ -z "${2:-}" ]; then
          log_warn "[main] ⚠ --engine requires a value (trt|vllm)"
          return 1
        fi
        engine="$2"
        shift
        ;;
      --engine=*)
        engine="${1#--engine=}"
        ;;
      --vllm)
        engine="vllm"
        ;;
      --trt|--tensorrt)
        engine="trt"
        ;;
      --deploy-mode)
        if [ -z "${2:-}" ]; then
          log_warn "[main] ⚠ --deploy-mode requires a value (both|chat|tool)"
          return 1
        fi
        deploy_mode="$2"
        deploy_explicit=1
        shift
        ;;
      --deploy-mode=*)
        deploy_mode="${1#--deploy-mode=}"
        deploy_explicit=1
        ;;
      4bit|4BIT|4Bit)
        quant_type="4bit"
        ;;
      8bit|8BIT|8Bit)
        quant_type="8bit"
        ;;
      awq|AWQ|fp8|FP8)
        log_err "[main] ✗ '${1}' flag has been removed. Use '4bit' or '8bit' explicitly."
        return 1
        ;;
      chat|tool|both)
        if [ ${#positional_args[@]} -eq 0 ] && [ "${deploy_explicit}" -eq 0 ]; then
          deploy_mode="$1"
          deploy_explicit=1
        else
          positional_args+=("$1")
        fi
        ;;
      --*)
        log_warn "[main] ⚠ Unknown flag '$1' ignored"
        ;;
      *)
        positional_args+=("$1")
        ;;
    esac
    shift
  done

  if [ "${deploy_explicit}" -eq 0 ] && [ ${#positional_args[@]} -gt 0 ]; then
    local last_index=$(( ${#positional_args[@]} - 1 ))
    local maybe_mode="${positional_args[$last_index]}"
    case "${maybe_mode}" in
      chat|tool|both)
        deploy_mode="${maybe_mode}"
        unset "positional_args[$last_index]"
        ;;
    esac
  fi

  case "${deploy_mode}" in
    both|chat|tool) ;;
    *)
      log_warn "[main] ⚠ Invalid deploy mode '${deploy_mode}', defaulting to 'both'"
      deploy_mode="both"
      ;;
  esac

  case "${engine}" in
    vllm|VLLM)
      engine="vllm"
      ;;
    trt|TRT|tensorrt|TENSORRT|trtllm|TRTLLM)
      engine="trt"
      ;;
    *)
      log_warn "[main] ⚠ Unknown engine type '${engine}', defaulting to 'trt'"
      engine="trt"
      ;;
  esac

  case "${quant_type}" in
    4bit|8bit|auto) ;;
    *)
      quant_type="auto"
      ;;
  esac

  local chat_model=""
  local tool_model=""

  case "${deploy_mode}" in
    both)
      if [ ${#positional_args[@]} -lt 2 ]; then
        log_warn "[main] ⚠ both mode requires <chat_model> <tool_model>"
        return 1
      fi
      chat_model="${positional_args[0]}"
      tool_model="${positional_args[1]}"
      if [ ${#positional_args[@]} -gt 2 ]; then
        log_warn "[main] ⚠ Extra arguments ignored after <chat_model> <tool_model>"
      fi
      ;;
    chat)
      if [ ${#positional_args[@]} -lt 1 ]; then
        log_warn "[main] ⚠ chat-only mode requires <chat_model>"
        return 1
      fi
      chat_model="${positional_args[0]}"
      if [ ${#positional_args[@]} -gt 1 ]; then
        log_warn "[main] ⚠ Extra arguments ignored after <chat_model>"
      fi
      ;;
    tool)
      if [ ${#positional_args[@]} -lt 1 ]; then
        log_warn "[main] ⚠ tool-only mode requires <tool_model>"
        return 1
      fi
      tool_model="${positional_args[0]}"
      if [ ${#positional_args[@]} -gt 1 ]; then
        log_warn "[main] ⚠ Extra arguments ignored after <tool_model>"
      fi
      ;;
  esac

  if [ "${deploy_mode}" != "tool" ] && [ -z "${chat_model}" ]; then
    log_warn "[main] ⚠ CHAT_MODEL is required for deploy mode '${deploy_mode}'"
    return 1
  fi
  if [ "${deploy_mode}" != "chat" ] && [ -z "${tool_model}" ]; then
    log_warn "[main] ⚠ TOOL_MODEL is required for deploy mode '${deploy_mode}'"
    return 1
  fi

  ENGINE_TYPE="${engine}"
  INFERENCE_ENGINE="${engine}"
  PUSH_QUANT="${push_quant_requested}"
  HF_AWQ_PUSH_REQUESTED="${push_quant_requested}"
  HF_AWQ_PUSH=0
  QUANT_TYPE="${quant_type}"
  DEPLOY_MODE="${deploy_mode}"
  DEPLOY_MODE_SELECTED="${deploy_mode}"
  CHAT_MODEL_NAME="${chat_model}"
  TOOL_MODEL_NAME="${tool_model}"

  export ENGINE_TYPE INFERENCE_ENGINE
  export PUSH_QUANT HF_AWQ_PUSH HF_AWQ_PUSH_REQUESTED
  export QUANT_TYPE DEPLOY_MODE DEPLOY_MODE_SELECTED
  export CHAT_MODEL_NAME TOOL_MODEL_NAME

  return 0
}

# Export models to environment variables
main_export_models() {
  if [ "${DEPLOY_MODE}" = "both" ] || [ "${DEPLOY_MODE}" = "chat" ]; then
    export CHAT_MODEL="${CHAT_MODEL_NAME}"
  fi
  if [ "${DEPLOY_MODE}" = "both" ] || [ "${DEPLOY_MODE}" = "tool" ]; then
    export TOOL_MODEL="${TOOL_MODEL_NAME}"
  fi
}

