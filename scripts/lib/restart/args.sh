#!/usr/bin/env bash
# shellcheck disable=SC1091
# =============================================================================
# Restart Script Argument Parser
# =============================================================================
# Argument parsing for scripts/restart.sh. Handles deploy mode, engine flags,
# model reconfiguration, and dependency installation options.

_RESTART_ARGS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../common/args.sh
source "${_RESTART_ARGS_DIR}/../common/args.sh"
# shellcheck source=../../config/values/core.sh
source "${_RESTART_ARGS_DIR}/../../config/values/core.sh"
# shellcheck source=../../config/patterns.sh
source "${_RESTART_ARGS_DIR}/../../config/patterns.sh"

_restart_args_record_engine_flag() {
  if [ -z "${RESTART_ARGS_FIRST_ENGINE_FLAG}" ]; then
    RESTART_ARGS_FIRST_ENGINE_FLAG="${ENGINE_FLAG_NAME}"
  fi
  RESTART_ARGS_DEFERRED_ENGINE_FLAGS+=("${ENGINE_FLAG_NAME}")
  if [ "${ENGINE_FLAG_NAME}" = "--engine" ]; then
    RESTART_ARGS_DEFERRED_ENGINE_FLAGS+=("${ENGINE_FLAG_VALUE}")
  fi
}

_restart_args_handle_token() {
  case "$1" in
    "${CFG_DEPLOY_MODE_BOTH}" | "${CFG_DEPLOY_MODE_CHAT}" | "${CFG_DEPLOY_MODE_TOOL}")
      if [ -z "${DEPLOY_MODE}" ]; then
        DEPLOY_MODE="$1"
      fi
      if [ -z "${RECONFIG_DEPLOY_MODE}" ]; then
        RECONFIG_DEPLOY_MODE="$1"
      fi
      return 0
      ;;
    --install-deps)
      INSTALL_DEPS=1
      return 0
      ;;
    --reset-models | --reconfigure)
      RESTART_MODEL_MODE="reconfigure"
      return 0
      ;;
    --keep-models)
      RESTART_MODEL_MODE="reuse"
      return 0
      ;;
    --deploy-mode)
      cli_set_deploy_mode_value "${2:-}" "[restart]" RECONFIG_DEPLOY_MODE || return 1
      ARGS_SHIFT_COUNT=2
      return 0
      ;;
    --deploy-mode=*)
      cli_set_deploy_mode_value "${1#*=}" "[restart]" RECONFIG_DEPLOY_MODE || return 1
      return 0
      ;;
    --chat-quant)
      if [ -z "${2:-}" ]; then
        log_err "[restart] ✗ --chat-quant requires a value (4bit|8bit|fp8|gptq|gptq_marlin|awq)"
        return 1
      fi
      RECONFIG_CHAT_QUANTIZATION="$2"
      ARGS_SHIFT_COUNT=2
      return 0
      ;;
    --chat-quant=*)
      RECONFIG_CHAT_QUANTIZATION="${1#*=}"
      return 0
      ;;
    --chat-model)
      if [ -z "${2:-}" ]; then
        log_err "[restart] ✗ --chat-model requires a value"
        return 1
      fi
      RECONFIG_CHAT_MODEL="$2"
      ARGS_SHIFT_COUNT=2
      return 0
      ;;
    --chat-model=*)
      RECONFIG_CHAT_MODEL="${1#*=}"
      return 0
      ;;
    --tool-model)
      if [ -z "${2:-}" ]; then
        log_err "[restart] ✗ --tool-model requires a value"
        return 1
      fi
      RECONFIG_TOOL_MODEL="$2"
      ARGS_SHIFT_COUNT=2
      return 0
      ;;
    --tool-model=*)
      RECONFIG_TOOL_MODEL="${1#*=}"
      return 0
      ;;
    --help | -h)
      return 2
      ;;
    -*)
      log_err "[restart] ✗ Unknown flag '$1'. See --help for supported options."
      return 1
      ;;
    *)
      log_err "[restart] ✗ Unknown argument '$1'."
      return 1
      ;;
  esac
}

_restart_args_require_deploy_mode() {
  if [ -n "${DEPLOY_MODE}" ] || [ -n "${RECONFIG_DEPLOY_MODE}" ]; then
    return 0
  fi

  log_err "[restart] ✗ Deploy mode is required."
  log_err "[restart]   You must specify one of: both, chat, or tool"
  log_blank
  log_err "[restart]   Examples:"
  log_err "[restart]     bash scripts/restart.sh both"
  log_err "[restart]     bash scripts/restart.sh chat --vllm"
  log_err "[restart]     bash scripts/restart.sh --deploy-mode tool"
  return 1
}

_restart_args_apply_engine_flags() {
  if ! DEPLOY_MODE="$(cli_validate_deploy_mode "${DEPLOY_MODE:-${RECONFIG_DEPLOY_MODE:-${CFG_DEFAULT_DEPLOY_MODE}}}")"; then
    log_err "[restart] ✗ Invalid deploy mode '${DEPLOY_MODE}'. Expected both|chat|tool."
    return 1
  fi

  if [ "${DEPLOY_MODE}" = "${CFG_DEPLOY_MODE_TOOL}" ]; then
    if [ ${#RESTART_ARGS_DEFERRED_ENGINE_FLAGS[@]} -gt 0 ]; then
      log_err "[restart] ✗ ${RESTART_ARGS_FIRST_ENGINE_FLAG} is not supported when DEPLOY_MODE='tool'."
      log_err "[restart] ✗ Remove engine flags (--trt/--vllm/--engine) for tool-only deployments."
      return 1
    fi
    unset INFERENCE_ENGINE
    return 0
  fi

  apply_deferred_engine_flags "[restart]" "${RESTART_ARGS_DEFERRED_ENGINE_FLAGS[@]}"
}

parse_args() {
  init_common_state

  DEPLOY_MODE=""
  INSTALL_DEPS="${INSTALL_DEPS:-0}"
  RESTART_MODEL_MODE="${RESTART_MODEL_MODE:-reuse}"
  RECONFIG_DEPLOY_MODE="${RECONFIG_DEPLOY_MODE:-}"
  RECONFIG_CHAT_MODEL="${RECONFIG_CHAT_MODEL:-}"
  RECONFIG_TOOL_MODEL="${RECONFIG_TOOL_MODEL:-}"
  RECONFIG_CHAT_QUANTIZATION="${RECONFIG_CHAT_QUANTIZATION:-}"
  RESTART_ARGS_FIRST_ENGINE_FLAG=""
  RESTART_ARGS_DEFERRED_ENGINE_FLAGS=()

  while [ $# -gt 0 ]; do
    if parse_common_non_engine_flag "$1" "${2:-}"; then
      shift "${ARGS_SHIFT_COUNT}"
      continue
    fi

    local engine_parse_rc=0
    if parse_engine_flag_token "$1" "${2:-}"; then
      _restart_args_record_engine_flag
      shift "${ARGS_SHIFT_COUNT}"
      continue
    else
      engine_parse_rc=$?
    fi
    if [ "${engine_parse_rc}" -eq 2 ]; then
      log_err "[restart] ✗ --engine requires a value (trt|vllm)"
      return 1
    fi

    ARGS_SHIFT_COUNT=1
    _restart_args_handle_token "$1" "${2:-}"
    case $? in
      0) shift "${ARGS_SHIFT_COUNT}" ;;
      2) return 2 ;;
      *) return 1 ;;
    esac
  done

  _restart_args_require_deploy_mode || return 1
  _restart_args_apply_engine_flags || return 1

  if ! validate_common_state; then
    return 1
  fi

  export_common_state
  export INSTALL_DEPS DEPLOY_MODE
  export RESTART_MODEL_MODE RECONFIG_DEPLOY_MODE
  export RECONFIG_CHAT_MODEL RECONFIG_TOOL_MODEL
  export RECONFIG_CHAT_QUANTIZATION
  return 0
}
