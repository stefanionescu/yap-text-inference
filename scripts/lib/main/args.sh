#!/usr/bin/env bash
# shellcheck disable=SC1091
# =============================================================================
# Main Script Argument Parser
# =============================================================================
# Argument parsing for main.sh. Performs single-pass parsing of engine flags,
# quantization shortcuts, deploy modes, and model arguments.

_MAIN_ARGS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../common/args.sh
source "${_MAIN_ARGS_DIR}/../common/args.sh"
# shellcheck source=../../config/values/core.sh
source "${_MAIN_ARGS_DIR}/../../config/values/core.sh"
# shellcheck source=../../config/patterns.sh
source "${_MAIN_ARGS_DIR}/../../config/patterns.sh"

parse_cli() {
  init_common_state

  local quant_type="auto"
  local deploy_mode="${DEPLOY_MODE:-${CFG_DEFAULT_DEPLOY_MODE}}"
  local deploy_explicit=0
  local first_engine_flag=""
  local -a positional_args=()
  local -a deferred_engine_flags=()

  while [ $# -gt 0 ]; do
    # Parse non-engine common flags first.
    if parse_common_non_engine_flag "$1" "${2:-}"; then
      shift "${ARGS_SHIFT_COUNT}"
      continue
    fi

    # Defer engine handling until deploy mode is known.
    local engine_parse_rc=0
    if parse_engine_flag_token "$1" "${2:-}"; then
      engine_parse_rc=0
    else
      engine_parse_rc=$?
    fi
    case "${engine_parse_rc}" in
      0)
        if [ -z "${first_engine_flag}" ]; then
          first_engine_flag="${ENGINE_FLAG_NAME}"
        fi
        deferred_engine_flags+=("${ENGINE_FLAG_NAME}")
        if [ "${ENGINE_FLAG_NAME}" = "--engine" ]; then
          deferred_engine_flags+=("${ENGINE_FLAG_VALUE}")
        fi
        shift "${ARGS_SHIFT_COUNT}"
        continue
        ;;
      2)
        log_err "[main] ✗ --engine requires a value (trt|vllm)"
        return 1
        ;;
    esac

    case "$1" in
      -h | --help)
        show_usage
        return 1
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
      4bit | 4BIT | 4Bit)
        quant_type="4bit"
        ;;
      8bit | 8BIT | 8Bit)
        quant_type="8bit"
        ;;
      awq | AWQ | fp8 | FP8)
        log_err "[main] ✗ '${1}' flag has been removed. Use '4bit' or '8bit' explicitly."
        return 1
        ;;
      "${CFG_DEPLOY_MODE_CHAT}" | "${CFG_DEPLOY_MODE_TOOL}" | "${CFG_DEPLOY_MODE_BOTH}")
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
    local last_index=$((${#positional_args[@]} - 1))
    local maybe_mode="${positional_args[$last_index]}"
    case "${maybe_mode}" in
      "${CFG_DEPLOY_MODE_CHAT}" | "${CFG_DEPLOY_MODE_TOOL}" | "${CFG_DEPLOY_MODE_BOTH}")
        deploy_mode="${maybe_mode}"
        unset "positional_args[$last_index]"
        ;;
    esac
  fi

  if ! deploy_mode="$(cli_validate_deploy_mode "${deploy_mode}")"; then
    log_err "[main] ✗ Invalid deploy mode '${deploy_mode}'. Expected both|chat|tool."
    return 1
  fi

  if [ "${deploy_mode}" = "${CFG_DEPLOY_MODE_TOOL}" ]; then
    if [ ${#deferred_engine_flags[@]} -gt 0 ]; then
      log_err "[main] ✗ ${first_engine_flag} is not supported when DEPLOY_MODE='tool'."
      log_err "[main] ✗ Remove engine flags (--trt/--vllm/--engine) for tool-only deployments."
      return 1
    fi
    unset INFERENCE_ENGINE
  else
    if ! apply_deferred_engine_flags "[main]" "${deferred_engine_flags[@]}"; then
      return 1
    fi
  fi

  case "${quant_type}" in
    4bit | 8bit | auto) ;;
    *)
      quant_type="auto"
      ;;
  esac

  local chat_model=""
  local tool_model=""

  case "${deploy_mode}" in
    "${CFG_DEPLOY_MODE_BOTH}")
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
    "${CFG_DEPLOY_MODE_CHAT}")
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
    "${CFG_DEPLOY_MODE_TOOL}")
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

  if [ "${deploy_mode}" != "${CFG_DEPLOY_MODE_TOOL}" ] && [ -z "${chat_model}" ]; then
    log_warn "[main] ⚠ CHAT_MODEL is required for deploy mode '${deploy_mode}'"
    return 1
  fi
  if [ "${deploy_mode}" != "${CFG_DEPLOY_MODE_CHAT}" ] && [ -z "${tool_model}" ]; then
    log_warn "[main] ⚠ TOOL_MODEL is required for deploy mode '${deploy_mode}'"
    return 1
  fi

  QUANT_TYPE="${quant_type}"
  DEPLOY_MODE="${deploy_mode}"
  CHAT_MODEL_NAME="${chat_model}"
  TOOL_MODEL_NAME="${tool_model}"

  # Validate mutually exclusive flags
  if ! validate_common_state; then
    return 1
  fi

  export_common_state
  export QUANT_TYPE DEPLOY_MODE
  export CHAT_MODEL_NAME TOOL_MODEL_NAME

  return 0
}

# Export models to environment variables
export_models() {
  if [ "${DEPLOY_MODE:-}" = "${CFG_DEPLOY_MODE_BOTH}" ] || [ "${DEPLOY_MODE:-}" = "${CFG_DEPLOY_MODE_CHAT}" ]; then
    export CHAT_MODEL="${CHAT_MODEL_NAME:-}"
  fi
  if [ "${DEPLOY_MODE:-}" = "${CFG_DEPLOY_MODE_BOTH}" ] || [ "${DEPLOY_MODE:-}" = "${CFG_DEPLOY_MODE_TOOL}" ]; then
    export TOOL_MODEL="${TOOL_MODEL_NAME:-}"
  fi
}
