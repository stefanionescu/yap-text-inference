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
  RECONFIG_QUANTIZATION="${RECONFIG_QUANTIZATION:-}"
  HF_AWQ_PUSH=0
  
  # Engine selection - default from environment or 'trt'
  INFERENCE_ENGINE="${INFERENCE_ENGINE:-trt}"

  while [ $# -gt 0 ]; do
    case "$1" in
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
        if [ -z "${2:-}" ]; then return 2; fi
        INFERENCE_ENGINE="$2"
        shift 2
        ;;
      --engine=*)
        INFERENCE_ENGINE="${1#*=}"
        shift
        ;;
      --install-deps)
        INSTALL_DEPS=1
        shift
        ;;
      --no-install-deps)
        INSTALL_DEPS=0
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
        if [ -z "${2:-}" ]; then return 2; fi
        RECONFIG_DEPLOY_MODE="$2"
        shift 2
        ;;
      --deploy-mode=*)
        RECONFIG_DEPLOY_MODE="${1#*=}"
        shift
        ;;
      --chat-quant)
        if [ -z "${2:-}" ]; then return 2; fi
        RECONFIG_CHAT_QUANTIZATION="$2"
        shift 2
        ;;
      --chat-quant=*)
        RECONFIG_CHAT_QUANTIZATION="${1#*=}"
        shift
        ;;
      --chat-model)
        if [ -z "${2:-}" ]; then return 2; fi
        RECONFIG_CHAT_MODEL="$2"
        shift 2
        ;;
      --chat-model=*)
        RECONFIG_CHAT_MODEL="${1#*=}"
        shift
        ;;
      --tool-model)
        if [ -z "${2:-}" ]; then return 2; fi
        RECONFIG_TOOL_MODEL="$2"
        shift 2
        ;;
      --tool-model=*)
        RECONFIG_TOOL_MODEL="${1#*=}"
        shift
        ;;
      --quant)
        if [ -z "${2:-}" ]; then return 2; fi
        RECONFIG_QUANTIZATION="$2"
        shift 2
        ;;
      --quant=*)
        RECONFIG_QUANTIZATION="${1#*=}"
        shift
        ;;
      --push-quant)
        HF_AWQ_PUSH=1
        shift
        ;;
      --no-push-quant)
        HF_AWQ_PUSH=0
        shift
        ;;
      --help|-h)
        return 2
        ;;
      *)
        shift
        ;;
    esac
  done

  DEPLOY_MODE="${DEPLOY_MODE:-both}"
  
  # Normalize engine selection
  case "${INFERENCE_ENGINE}" in
    trt|TRT|tensorrt|TENSORRT) INFERENCE_ENGINE="trt" ;;
    vllm|VLLM) INFERENCE_ENGINE="vllm" ;;
    *)
      log_warn "[restart] Unknown engine '${INFERENCE_ENGINE}', defaulting to 'trt'"
      INFERENCE_ENGINE="trt"
      ;;
  esac
  
  export INSTALL_DEPS DEPLOY_MODE INFERENCE_ENGINE
  export RESTART_MODEL_MODE RECONFIG_DEPLOY_MODE
  export RECONFIG_CHAT_MODEL RECONFIG_TOOL_MODEL
  export RECONFIG_CHAT_QUANTIZATION RECONFIG_QUANTIZATION
  export HF_AWQ_PUSH
  return 0
}


