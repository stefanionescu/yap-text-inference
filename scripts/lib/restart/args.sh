#!/usr/bin/env bash

# Argument parsing for scripts/restart.sh
# Requires: none (sets DEPLOY_MODE and INSTALL_DEPS)

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

  while [ $# -gt 0 ]; do
    case "$1" in
      both|chat|tool)
        if [ -z "${DEPLOY_MODE}" ]; then DEPLOY_MODE="$1"; fi
        if [ -z "${RECONFIG_DEPLOY_MODE}" ]; then RECONFIG_DEPLOY_MODE="$1"; fi
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
      --push-awq)
        log_warn "Flag --push-awq is deprecated; use --push-quant instead."
        HF_AWQ_PUSH=1
        shift
        ;;
      --no-push-awq)
        log_warn "Flag --no-push-awq is deprecated; use --no-push-quant instead."
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
  export INSTALL_DEPS DEPLOY_MODE
  export RESTART_MODEL_MODE RECONFIG_DEPLOY_MODE
  export RECONFIG_CHAT_MODEL RECONFIG_TOOL_MODEL
  export RECONFIG_CHAT_QUANTIZATION RECONFIG_QUANTIZATION
  export HF_AWQ_PUSH
  return 0
}


