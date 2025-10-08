#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

source "${SCRIPT_DIR}/utils.sh"

log_info "Starting Yap Text Inference Server"

# Usage function
usage() {
  echo "Usage:"
  echo "  $0 <quantization> <chat_model> <tool_model> [deploy_mode]"
  echo "  $0 <quantization> chat <chat_model>"
  echo "  $0 <quantization> tool <tool_model>"
  echo "  $0 <quantization> both <chat_model> <tool_model>"
  echo ""
  echo "Quantization options:"
  echo "  8bit  - Use 8-bit quantization (fp8)"
  echo "  4bit  - Use 4-bit quantization (GPTQ pre-quantized weights)"
  echo "  awq   - Use 4-bit AWQ via vLLM auto-AWQ (quantize float model on load)"
  echo ""
  echo "Chat model options:"
  echo "  For 8bit: SicariusSicariiStuff/Impish_Nemo_12B (12B, general purpose)"
  echo "           SicariusSicariiStuff/Wingless_Imp_8B (8B, roleplay/creative)"
  echo "           SicariusSicariiStuff/Impish_Mind_8B (8B, highest rated, uncensored)"
  echo "           kyx0r/Neona-12B (12B)"
  echo "           w4r10ck/SOLAR-10.7B-Instruct-v1.0-uncensored (10.7B, uncensored)"
  echo "  For 4bit (GPTQ): SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-64"
  echo "           SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-128"
  echo "           SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-32"
  echo "  For awq (float weights): SicariusSicariiStuff/Impish_Nemo_12B"
  echo "                          SicariusSicariiStuff/Wingless_Imp_8B"
  echo "                          SicariusSicariiStuff/Impish_Mind_8B"
  echo "                          kyx0r/Neona-12B"
  echo "                          w4r10ck/SOLAR-10.7B-Instruct-v1.0-uncensored"
  echo ""
  echo "Tool model options:"
  echo "  MadeAgents/Hammer2.1-1.5b"
  echo "  MadeAgents/Hammer2.1-3b"
  echo ""
  echo "Environment options:"
  echo "  CONCURRENT_MODEL_CALL=1       - Enable concurrent model calls (default: 0=sequential)"
  echo "  DEPLOY_MODELS=both|chat|tool  - Which models to deploy (default: both)"
  echo ""
  echo "Examples:"
  echo "  # Sequential mode (default)"
  echo "  $0 8bit SicariusSicariiStuff/Impish_Nemo_12B MadeAgents/Hammer2.1-1.5b"
  echo ""
  echo "  # 8B roleplay model"
  echo "  $0 8bit SicariusSicariiStuff/Wingless_Imp_8B MadeAgents/Hammer2.1-1.5b"
  echo ""
  echo "  # 8B highest rated uncensored model"
  echo "  $0 8bit SicariusSicariiStuff/Impish_Mind_8B MadeAgents/Hammer2.1-1.5b"
  echo ""
  echo "  # Concurrent mode for lower latency"
  echo "  CONCURRENT_MODEL_CALL=1 $0 8bit SicariusSicariiStuff/Impish_Nemo_12B MadeAgents/Hammer2.1-3b"
  echo ""
  echo "  # 4-bit GPTQ with concurrent mode"
  echo "  CONCURRENT_MODEL_CALL=1 $0 4bit SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-64 MadeAgents/Hammer2.1-3b"
  echo ""
  echo "  # 4-bit AWQ (quantize both chat and tool models on load)"
  echo "  $0 awq SicariusSicariiStuff/Impish_Nemo_12B MadeAgents/Hammer2.1-1.5b"
  echo ""
  echo "  # Chat-only deployment"
  echo "  $0 8bit chat SicariusSicariiStuff/Impish_Nemo_12B"
  echo "  DEPLOY_MODELS=chat $0 8bit SicariusSicariiStuff/Impish_Nemo_12B MadeAgents/Hammer2.1-1.5b"
  echo ""
  echo "  # Tool-only deployment"
  echo "  $0 8bit tool MadeAgents/Hammer2.1-1.5b"
  echo "  DEPLOY_MODELS=tool $0 8bit SicariusSicariiStuff/Impish_Nemo_12B MadeAgents/Hammer2.1-1.5b"
  exit 1
}

# Parse and normalize arguments
if [ $# -lt 2 ]; then
  log_warn "Error: Not enough arguments"
  usage
fi

QUANT_TYPE="$1"; shift

# Defaults that we may fill from args
CHAT_MODEL_NAME=""
TOOL_MODEL_NAME=""
DEPLOY_MODE_SELECTED="${DEPLOY_MODELS:-}"

case "${1:-}" in
  chat)
    DEPLOY_MODE_SELECTED="chat"
    shift
    if [ $# -lt 1 ]; then
      log_warn "Error: chat-only mode requires <chat_model>"
      usage
    fi
    CHAT_MODEL_NAME="$1"; shift
    ;;
  tool)
    DEPLOY_MODE_SELECTED="tool"
    shift
    if [ $# -lt 1 ]; then
      log_warn "Error: tool-only mode requires <tool_model>"
      usage
    fi
    TOOL_MODEL_NAME="$1"; shift
    ;;
  both)
    DEPLOY_MODE_SELECTED="both"
    shift
    if [ $# -lt 2 ]; then
      log_warn "Error: both mode requires <chat_model> <tool_model>"
      usage
    fi
    CHAT_MODEL_NAME="$1"; TOOL_MODEL_NAME="$2"; shift 2
    ;;
  *)
    # Backward-compatible form: <chat_model> <tool_model> [deploy_mode]
    if [ $# -lt 2 ]; then
      log_warn "Error: Must specify <chat_model> <tool_model> or use 'chat|tool' form"
      usage
    fi
    CHAT_MODEL_NAME="$1"; TOOL_MODEL_NAME="$2"; shift 2
    DEPLOY_MODE_SELECTED="${1:-${DEPLOY_MODE_SELECTED:-both}}"
    ;;
esac

# Normalize and validate deploy mode selection
case "${DEPLOY_MODE_SELECTED:-both}" in
  both|chat|tool)
    export DEPLOY_MODELS="${DEPLOY_MODE_SELECTED:-both}"
    ;;
  *)
    log_warn "Invalid deploy_mode '${DEPLOY_MODE_SELECTED}', defaulting to 'both'"
    export DEPLOY_MODELS=both
    ;;
esac

# Validate quantization type and chat model
case "${QUANT_TYPE}" in
  8bit)
    export QUANTIZATION=fp8
    if [ "${CHAT_MODEL_NAME}" != "SicariusSicariiStuff/Impish_Nemo_12B" ] && 
       [ "${CHAT_MODEL_NAME}" != "SicariusSicariiStuff/Wingless_Imp_8B" ] &&
       [ "${CHAT_MODEL_NAME}" != "SicariusSicariiStuff/Impish_Mind_8B" ] &&
       [ "${CHAT_MODEL_NAME}" != "kyx0r/Neona-12B" ] &&
       [ "${CHAT_MODEL_NAME}" != "w4r10ck/SOLAR-10.7B-Instruct-v1.0-uncensored" ]; then
      log_warn "Error: For 8bit quantization, must use one of:"
      log_warn "  SicariusSicariiStuff/Impish_Nemo_12B (12B, general purpose)"
      log_warn "  SicariusSicariiStuff/Wingless_Imp_8B (8B, roleplay/creative)"
      log_warn "  SicariusSicariiStuff/Impish_Mind_8B (8B, highest rated, uncensored)"
      log_warn "  kyx0r/Neona-12B (12B)"
      log_warn "  w4r10ck/SOLAR-10.7B-Instruct-v1.0-uncensored (10.7B, uncensored)"
      usage
    fi
    ;;
  4bit)
    export QUANTIZATION=gptq_marlin
    if [ "${CHAT_MODEL_NAME}" != "SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-64" ] && 
       [ "${CHAT_MODEL_NAME}" != "SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-128" ] &&
       [ "${CHAT_MODEL_NAME}" != "SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-32" ]; then
      log_warn "Error: For 4bit (GPTQ) quantization, must use one of:"
      log_warn "  SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-64"
      log_warn "  SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-128"
      log_warn "  SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-32"
      usage
    fi
    ;;
  awq)
    export QUANTIZATION=awq
    # AWQ requires float (non-GPTQ) chat model; tool will be quantized too
    case "${CHAT_MODEL_NAME}" in
      "SicariusSicariiStuff/Impish_Nemo_12B"|
      "SicariusSicariiStuff/Wingless_Imp_8B"|
      "SicariusSicariiStuff/Impish_Mind_8B"|
      "kyx0r/Neona-12B"|
      "w4r10ck/SOLAR-10.7B-Instruct-v1.0-uncensored")
        ;;
      *)
        log_warn "Error: For awq, provide a FLOAT chat model (not GPTQ)."
        log_warn "  Allowed examples:"
        log_warn "    SicariusSicariiStuff/Impish_Nemo_12B"
        log_warn "    SicariusSicariiStuff/Wingless_Imp_8B"
        log_warn "    SicariusSicariiStuff/Impish_Mind_8B"
        log_warn "    kyx0r/Neona-12B"
        log_warn "    w4r10ck/SOLAR-10.7B-Instruct-v1.0-uncensored"
        usage
        ;;
    esac
    ;;
  *)
    log_warn "Error: Invalid quantization '${QUANT_TYPE}'. Must be '8bit', '4bit', or 'awq'"
    usage
    ;;
esac

# Note: Model & quantization validation is centralized in Python (src/config.py).
# main.sh only passes through the selected values.

# Export only what is needed for selected deployment
if [ "${DEPLOY_MODELS}" = "both" ] || [ "${DEPLOY_MODELS}" = "chat" ]; then
  export CHAT_MODEL="${CHAT_MODEL_NAME}"
fi
if [ "${DEPLOY_MODELS}" = "both" ] || [ "${DEPLOY_MODELS}" = "tool" ]; then
  export TOOL_MODEL="${TOOL_MODEL_NAME}"
fi

# Display configuration
CONCURRENT_STATUS="concurrent (default)"
if [ "${CONCURRENT_MODEL_CALL:-1}" = "0" ]; then
  CONCURRENT_STATUS="sequential (override)"
fi

log_info "Configuration: ${QUANT_TYPE} quantization"
log_info "  Deploy mode: ${DEPLOY_MODELS}"
log_info "  Chat model: ${CHAT_MODEL_NAME}"
log_info "  Tool model: ${TOOL_MODEL_NAME}"
log_info "  Model calls: ${CONCURRENT_STATUS}"

bash "${SCRIPT_DIR}/01_check_gpu.sh"
bash "${SCRIPT_DIR}/02_python_env.sh"
bash "${SCRIPT_DIR}/03_install_deps.sh"
source "${SCRIPT_DIR}/04_env_defaults.sh"
bash "${SCRIPT_DIR}/05_start_server.sh"
bash "${SCRIPT_DIR}/06_follow_logs.sh"


