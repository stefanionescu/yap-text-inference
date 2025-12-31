#!/usr/bin/env bash

# Argument parsing for scripts/restart.sh
# Requires: none (sets DEPLOY_MODE, INSTALL_DEPS, INFERENCE_ENGINE)

restart_parse_args() {
  DEPLOY_MODE=""
  INSTALL_DEPS="${INSTALL_DEPS:-0}"
  RESTART_MODEL_MODE="${RESTART_MODEL_MODE:-reuse}"
  RECONFIG_DEPLOY_MODE="${RECONFIG_DEPLOY_MODE:-}"
  RECONFIG_CHAT_MODEL="${RECONFIG_CHAT_MODEL:-}"
  RECONFIG_TOOL_MODEL="${RECONFIG_TOOL_MODEL:-}"
  RECONFIG_CHAT_QUANTIZATION="${RECONFIG_CHAT_QUANTIZATION:-}"
  HF_AWQ_PUSH_REQUESTED="${HF_AWQ_PUSH_REQUESTED:-0}"
  HF_AWQ_PUSH=0
  HF_ENGINE_PUSH_REQUESTED="${HF_ENGINE_PUSH_REQUESTED:-0}"
  HF_ENGINE_PUSH=0
  SHOW_HF_LOGS="${SHOW_HF_LOGS:-0}"
  SHOW_TRT_LOGS="${SHOW_TRT_LOGS:-0}"
  SHOW_VLLM_LOGS="${SHOW_VLLM_LOGS:-0}"
  SHOW_LLMCOMPRESSOR_LOGS="${SHOW_LLMCOMPRESSOR_LOGS:-0}"
  
  # Engine selection - default from environment or 'trt'
  INFERENCE_ENGINE="${INFERENCE_ENGINE:-trt}"

  while [ $# -gt 0 ]; do
    case "$1" in
      --show-hf-logs)
        SHOW_HF_LOGS=1
        shift
        ;;
      --show-trt-logs)
        SHOW_TRT_LOGS=1
        shift
        ;;
      --show-vllm-logs)
        SHOW_VLLM_LOGS=1
        shift
        ;;
      --show-llmcompressor-logs)
        SHOW_LLMCOMPRESSOR_LOGS=1
        shift
        ;;
      both|chat|tool)
        if [ -z "${DEPLOY_MODE}" ]; then DEPLOY_MODE="$1"; fi
        if [ -z "${RECONFIG_DEPLOY_MODE}" ]; then RECONFIG_DEPLOY_MODE="$1"; fi
        shift
        ;;
      --trt)
        INFERENCE_ENGINE="trt"
        shift
        ;;
      --vllm)
        INFERENCE_ENGINE="vllm"
        shift
        ;;
      --engine)
        if ! cli_set_engine_value "${2:-}" "[restart]" INFERENCE_ENGINE; then
          return 1
        fi
        shift 2
        ;;
      --engine=*)
        cli_set_engine_value "${1#*=}" "[restart]" INFERENCE_ENGINE || return 1
        shift
        ;;
      --install-deps)
        INSTALL_DEPS=1
        shift
        ;;
      --reset-models|--reconfigure)
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
      --push-quant)
        HF_AWQ_PUSH_REQUESTED=1
        shift
        ;;
      --push-engine)
        HF_ENGINE_PUSH_REQUESTED=1
        shift
        ;;
      --help|-h)
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

  # Inherit from --deploy-mode flag if DEPLOY_MODE wasn't set as positional
  if ! DEPLOY_MODE="$(cli_validate_deploy_mode "${DEPLOY_MODE:-${RECONFIG_DEPLOY_MODE:-both}}")"; then
    log_err "[restart] ✗ Invalid deploy mode '${DEPLOY_MODE}'. Expected both|chat|tool."
    return 1
  fi
  
  # Normalize engine selection
  if ! INFERENCE_ENGINE="$(cli_normalize_engine "${INFERENCE_ENGINE}")"; then
    log_err "[restart] ✗ Unknown engine '${INFERENCE_ENGINE}'. Expected trt|vllm."
    return 1
  fi
  
  export INSTALL_DEPS DEPLOY_MODE INFERENCE_ENGINE
  export RESTART_MODEL_MODE RECONFIG_DEPLOY_MODE
  export RECONFIG_CHAT_MODEL RECONFIG_TOOL_MODEL
  export RECONFIG_CHAT_QUANTIZATION
  export HF_AWQ_PUSH HF_AWQ_PUSH_REQUESTED
  export HF_ENGINE_PUSH HF_ENGINE_PUSH_REQUESTED
  export SHOW_HF_LOGS SHOW_TRT_LOGS SHOW_VLLM_LOGS SHOW_LLMCOMPRESSOR_LOGS
  return 0
}
