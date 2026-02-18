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

parse_args() {
  init_common_state

  DEPLOY_MODE=""
  INSTALL_DEPS="${INSTALL_DEPS:-0}"
  RESTART_MODEL_MODE="${RESTART_MODEL_MODE:-reuse}"
  RECONFIG_DEPLOY_MODE="${RECONFIG_DEPLOY_MODE:-}"
  RECONFIG_CHAT_MODEL="${RECONFIG_CHAT_MODEL:-}"
  RECONFIG_TOOL_MODEL="${RECONFIG_TOOL_MODEL:-}"
  RECONFIG_CHAT_QUANTIZATION="${RECONFIG_CHAT_QUANTIZATION:-}"
  local first_engine_flag=""
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
        log_err "[restart] ✗ --engine requires a value (trt|vllm)"
        return 1
        ;;
    esac

    case "$1" in
      "${CFG_DEPLOY_MODE_BOTH}" | "${CFG_DEPLOY_MODE_CHAT}" | "${CFG_DEPLOY_MODE_TOOL}")
        if [ -z "${DEPLOY_MODE}" ]; then DEPLOY_MODE="$1"; fi
        if [ -z "${RECONFIG_DEPLOY_MODE}" ]; then RECONFIG_DEPLOY_MODE="$1"; fi
        shift
        ;;
      --install-deps)
        INSTALL_DEPS=1
        shift
        ;;
      --reset-models | --reconfigure)
        RESTART_MODEL_MODE="reconfigure"
        shift
        ;;
      --keep-models)
        RESTART_MODEL_MODE="reuse"
        shift
        ;;
      --deploy-mode)
        if ! cli_set_deploy_mode_value "${2:-}" "[restart]" RECONFIG_DEPLOY_MODE; then
          return 1
        fi
        shift 2
        ;;
      --deploy-mode=*)
        cli_set_deploy_mode_value "${1#*=}" "[restart]" RECONFIG_DEPLOY_MODE || return 1
        shift
        ;;
      --chat-quant)
        if [ -z "${2:-}" ]; then
          log_err "[restart] ✗ --chat-quant requires a value (4bit|8bit|fp8|gptq|gptq_marlin|awq)"
          return 1
        fi
        RECONFIG_CHAT_QUANTIZATION="$2"
        shift 2
        ;;
      --chat-quant=*)
        RECONFIG_CHAT_QUANTIZATION="${1#*=}"
        shift
        ;;
      --chat-model)
        if [ -z "${2:-}" ]; then
          log_err "[restart] ✗ --chat-model requires a value"
          return 1
        fi
        RECONFIG_CHAT_MODEL="$2"
        shift 2
        ;;
      --chat-model=*)
        RECONFIG_CHAT_MODEL="${1#*=}"
        shift
        ;;
      --tool-model)
        if [ -z "${2:-}" ]; then
          log_err "[restart] ✗ --tool-model requires a value"
          return 1
        fi
        RECONFIG_TOOL_MODEL="$2"
        shift 2
        ;;
      --tool-model=*)
        RECONFIG_TOOL_MODEL="${1#*=}"
        shift
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
  done

  # REQUIRE deploy mode to be explicitly specified (no default)
  if [ -z "${DEPLOY_MODE}" ] && [ -z "${RECONFIG_DEPLOY_MODE}" ]; then
    log_err "[restart] ✗ Deploy mode is required."
    log_err "[restart]   You must specify one of: both, chat, or tool"
    log_blank
    log_err "[restart]   Examples:"
    log_err "[restart]     bash scripts/restart.sh both"
    log_err "[restart]     bash scripts/restart.sh chat --vllm"
    log_err "[restart]     bash scripts/restart.sh --deploy-mode tool"
    return 1
  fi

  # Inherit from --deploy-mode flag if DEPLOY_MODE wasn't set as positional
  if ! DEPLOY_MODE="$(cli_validate_deploy_mode "${DEPLOY_MODE:-${RECONFIG_DEPLOY_MODE:-${CFG_DEFAULT_DEPLOY_MODE}}}")"; then
    log_err "[restart] ✗ Invalid deploy mode '${DEPLOY_MODE}'. Expected both|chat|tool."
    return 1
  fi

  if [ "${DEPLOY_MODE}" = "${CFG_DEPLOY_MODE_TOOL}" ]; then
    if [ ${#deferred_engine_flags[@]} -gt 0 ]; then
      log_err "[restart] ✗ ${first_engine_flag} is not supported when DEPLOY_MODE='tool'."
      log_err "[restart] ✗ Remove engine flags (--trt/--vllm/--engine) for tool-only deployments."
      return 1
    fi
    unset INFERENCE_ENGINE
  else
    if ! apply_deferred_engine_flags "[restart]" "${deferred_engine_flags[@]}"; then
      return 1
    fi
  fi

  # Validate mutually exclusive flags
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
