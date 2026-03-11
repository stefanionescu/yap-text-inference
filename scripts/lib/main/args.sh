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

_main_args_record_engine_flag() {
  if [ -z "${MAIN_ARGS_FIRST_ENGINE_FLAG}" ]; then
    MAIN_ARGS_FIRST_ENGINE_FLAG="${ENGINE_FLAG_NAME}"
  fi
  MAIN_ARGS_DEFERRED_ENGINE_FLAGS+=("${ENGINE_FLAG_NAME}")
  if [ "${ENGINE_FLAG_NAME}" = "--engine" ]; then
    MAIN_ARGS_DEFERRED_ENGINE_FLAGS+=("${ENGINE_FLAG_VALUE}")
  fi
}

_main_args_handle_token() {
  case "$1" in
    -h | --help)
      show_usage
      return 1
      ;;
    --deploy-mode)
      cli_set_deploy_mode_value "${2:-}" "[main]" MAIN_ARGS_DEPLOY_MODE || return 1
      MAIN_ARGS_DEPLOY_EXPLICIT=1
      ARGS_SHIFT_COUNT=2
      return 0
      ;;
    --deploy-mode=*)
      cli_set_deploy_mode_value "${1#--deploy-mode=}" "[main]" MAIN_ARGS_DEPLOY_MODE || return 1
      MAIN_ARGS_DEPLOY_EXPLICIT=1
      return 0
      ;;
    4bit | 4BIT | 4Bit)
      MAIN_ARGS_QUANT_TYPE="4bit"
      return 0
      ;;
    8bit | 8BIT | 8Bit)
      MAIN_ARGS_QUANT_TYPE="8bit"
      return 0
      ;;
    awq | AWQ | fp8 | FP8)
      log_err "[main] ✗ '${1}' flag has been removed. Use '4bit' or '8bit' explicitly."
      return 1
      ;;
    "${CFG_DEPLOY_MODE_CHAT}" | "${CFG_DEPLOY_MODE_TOOL}" | "${CFG_DEPLOY_MODE_BOTH}")
      if [ ${#MAIN_ARGS_POSITIONAL_ARGS[@]} -eq 0 ] && [ "${MAIN_ARGS_DEPLOY_EXPLICIT}" -eq 0 ]; then
        MAIN_ARGS_DEPLOY_MODE="$1"
        MAIN_ARGS_DEPLOY_EXPLICIT=1
      else
        MAIN_ARGS_POSITIONAL_ARGS+=("$1")
      fi
      return 0
      ;;
    --*)
      log_err "[main] ✗ Unknown flag '$1'. See --help for supported options."
      return 1
      ;;
    *)
      MAIN_ARGS_POSITIONAL_ARGS+=("$1")
      return 0
      ;;
  esac
}

_main_args_resolve_trailing_mode() {
  if [ "${MAIN_ARGS_DEPLOY_EXPLICIT}" -ne 0 ] || [ ${#MAIN_ARGS_POSITIONAL_ARGS[@]} -eq 0 ]; then
    return 0
  fi

  local last_index=$((${#MAIN_ARGS_POSITIONAL_ARGS[@]} - 1))
  local maybe_mode="${MAIN_ARGS_POSITIONAL_ARGS[$last_index]}"
  case "${maybe_mode}" in
    "${CFG_DEPLOY_MODE_CHAT}" | "${CFG_DEPLOY_MODE_TOOL}" | "${CFG_DEPLOY_MODE_BOTH}")
      MAIN_ARGS_DEPLOY_MODE="${maybe_mode}"
      unset "MAIN_ARGS_POSITIONAL_ARGS[$last_index]"
      ;;
  esac
}

_main_args_apply_engine_flags() {
  if ! DEPLOY_MODE="$(cli_validate_deploy_mode "${MAIN_ARGS_DEPLOY_MODE}")"; then
    log_err "[main] ✗ Invalid deploy mode '${MAIN_ARGS_DEPLOY_MODE}'. Expected both|chat|tool."
    return 1
  fi

  if [ "${DEPLOY_MODE}" = "${CFG_DEPLOY_MODE_TOOL}" ]; then
    if [ ${#MAIN_ARGS_DEFERRED_ENGINE_FLAGS[@]} -gt 0 ]; then
      log_err "[main] ✗ ${MAIN_ARGS_FIRST_ENGINE_FLAG} is not supported when DEPLOY_MODE='tool'."
      log_err "[main] ✗ Remove engine flags (--trt/--vllm/--engine) for tool-only deployments."
      return 1
    fi
    unset INFERENCE_ENGINE
    return 0
  fi

  apply_deferred_engine_flags "[main]" "${MAIN_ARGS_DEFERRED_ENGINE_FLAGS[@]}"
}

_main_args_resolve_models() {
  CHAT_MODEL_NAME=""
  TOOL_MODEL_NAME=""

  case "${DEPLOY_MODE}" in
    "${CFG_DEPLOY_MODE_BOTH}")
      if [ ${#MAIN_ARGS_POSITIONAL_ARGS[@]} -lt 2 ]; then
        log_warn "[main] ⚠ both mode requires <chat_model> <tool_model>"
        return 1
      fi
      CHAT_MODEL_NAME="${MAIN_ARGS_POSITIONAL_ARGS[0]}"
      TOOL_MODEL_NAME="${MAIN_ARGS_POSITIONAL_ARGS[1]}"
      if [ ${#MAIN_ARGS_POSITIONAL_ARGS[@]} -gt 2 ]; then
        log_err "[main] ✗ Extra arguments provided after <chat_model> <tool_model>: ${MAIN_ARGS_POSITIONAL_ARGS[*]:2}"
        return 1
      fi
      ;;
    "${CFG_DEPLOY_MODE_CHAT}")
      if [ ${#MAIN_ARGS_POSITIONAL_ARGS[@]} -lt 1 ]; then
        log_warn "[main] ⚠ chat-only mode requires <chat_model>"
        return 1
      fi
      CHAT_MODEL_NAME="${MAIN_ARGS_POSITIONAL_ARGS[0]}"
      if [ ${#MAIN_ARGS_POSITIONAL_ARGS[@]} -gt 1 ]; then
        log_err "[main] ✗ Extra arguments provided after <chat_model>: ${MAIN_ARGS_POSITIONAL_ARGS[*]:1}"
        return 1
      fi
      ;;
    "${CFG_DEPLOY_MODE_TOOL}")
      if [ ${#MAIN_ARGS_POSITIONAL_ARGS[@]} -lt 1 ]; then
        log_warn "[main] ⚠ tool-only mode requires <tool_model>"
        return 1
      fi
      TOOL_MODEL_NAME="${MAIN_ARGS_POSITIONAL_ARGS[0]}"
      if [ ${#MAIN_ARGS_POSITIONAL_ARGS[@]} -gt 1 ]; then
        log_warn "[main] ⚠ Extra arguments ignored after <tool_model>"
      fi
      ;;
  esac

  if [ "${DEPLOY_MODE}" != "${CFG_DEPLOY_MODE_TOOL}" ] && [ -z "${CHAT_MODEL_NAME}" ]; then
    log_warn "[main] ⚠ CHAT_MODEL is required for deploy mode '${DEPLOY_MODE}'"
    return 1
  fi
  if [ "${DEPLOY_MODE}" != "${CFG_DEPLOY_MODE_CHAT}" ] && [ -z "${TOOL_MODEL_NAME}" ]; then
    log_warn "[main] ⚠ TOOL_MODEL is required for deploy mode '${DEPLOY_MODE}'"
    return 1
  fi

  return 0
}

parse_cli() {
  init_common_state

  MAIN_ARGS_QUANT_TYPE="auto"
  MAIN_ARGS_DEPLOY_MODE="${DEPLOY_MODE:-${CFG_DEFAULT_DEPLOY_MODE}}"
  MAIN_ARGS_DEPLOY_EXPLICIT=0
  MAIN_ARGS_FIRST_ENGINE_FLAG=""
  MAIN_ARGS_POSITIONAL_ARGS=()
  MAIN_ARGS_DEFERRED_ENGINE_FLAGS=()

  while [ $# -gt 0 ]; do
    if parse_common_non_engine_flag "$1" "${2:-}"; then
      shift "${ARGS_SHIFT_COUNT}"
      continue
    fi

    local engine_parse_rc=0
    if parse_engine_flag_token "$1" "${2:-}"; then
      _main_args_record_engine_flag
      shift "${ARGS_SHIFT_COUNT}"
      continue
    else
      engine_parse_rc=$?
    fi
    if [ "${engine_parse_rc}" -eq 2 ]; then
      log_err "[main] ✗ --engine requires a value (trt|vllm)"
      return 1
    fi

    ARGS_SHIFT_COUNT=1
    _main_args_handle_token "$1" "${2:-}" || return 1
    shift "${ARGS_SHIFT_COUNT}"
  done

  _main_args_resolve_trailing_mode
  _main_args_apply_engine_flags || return 1

  case "${MAIN_ARGS_QUANT_TYPE}" in
    4bit | 8bit | auto) ;;
    *) MAIN_ARGS_QUANT_TYPE="auto" ;;
  esac

  _main_args_resolve_models || return 1
  QUANT_TYPE="${MAIN_ARGS_QUANT_TYPE}"

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
