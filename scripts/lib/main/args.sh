#!/usr/bin/env bash

# Argument parsing for main.sh.
# Performs a single-pass parse that understands every supported switch,
# quantization shorthand, and deploy-mode override. Parsed values are
# exported so downstream scripts do not need to re-process argv.

_MAIN_ARGS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../common/args.sh
source "${_MAIN_ARGS_DIR}/../common/args.sh"

main_parse_cli() {
  args_init_common_state

  local quant_type="auto"
  local deploy_mode="${DEPLOY_MODE:-both}"
  local deploy_explicit=0
  local -a positional_args=()

  while [ $# -gt 0 ]; do
    # Try common flags first
    if args_parse_common_flag "$1" "${2:-}"; then
      shift "${ARGS_SHIFT_COUNT}"
      continue
    fi

    case "$1" in
      -h|--help)
        main_usage
        return 1
        ;;
      --tensorrt)
        INFERENCE_ENGINE="trt"
        ;;
      --deploy-mode)
        if ! cli_set_deploy_mode_value "${2:-}" "[main]" deploy_mode; then
          return 1
        fi
        deploy_explicit=1
        shift
        ;;
      --deploy-mode=*)
        if ! cli_set_deploy_mode_value "${1#--deploy-mode=}" "[main]" deploy_mode; then
          return 1
        fi
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
        log_err "[main] ✗ Unknown flag '$1'. See --help for supported options."
        return 1
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

  if ! deploy_mode="$(cli_validate_deploy_mode "${deploy_mode}")"; then
    log_err "[main] ✗ Invalid deploy mode '${deploy_mode}'. Expected both|chat|tool."
    return 1
  fi

  if ! INFERENCE_ENGINE="$(cli_normalize_engine "${INFERENCE_ENGINE}")"; then
    log_err "[main] ✗ Unknown engine type '${INFERENCE_ENGINE}'. Expected trt|vllm."
    return 1
  fi

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
        log_err "[main] ✗ Extra arguments provided after <chat_model> <tool_model>: ${positional_args[*]:2}"
        return 1
      fi
      ;;
    chat)
      if [ ${#positional_args[@]} -lt 1 ]; then
        log_warn "[main] ⚠ chat-only mode requires <chat_model>"
        return 1
      fi
      chat_model="${positional_args[0]}"
      if [ ${#positional_args[@]} -gt 1 ]; then
        log_err "[main] ✗ Extra arguments provided after <chat_model>: ${positional_args[*]:1}"
        return 1
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

  QUANT_TYPE="${quant_type}"
  DEPLOY_MODE="${deploy_mode}"
  CHAT_MODEL_NAME="${chat_model}"
  TOOL_MODEL_NAME="${tool_model}"

  args_export_common_state
  export QUANT_TYPE DEPLOY_MODE
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
