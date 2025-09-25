#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

source "${SCRIPT_DIR}/utils.sh"

log_info "Starting Yap Text Inference Server"

# Usage function
usage() {
  echo "Usage: $0 <quantization> <chat_model> <tool_model>"
  echo ""
  echo "Quantization options:"
  echo "  8bit  - Use 8-bit quantization (fp8)"
  echo "  4bit  - Use 4-bit quantization (GPTQ)"
  echo ""
  echo "Chat model options:"
  echo "  For 8bit: SicariusSicariiStuff/Impish_Nemo_12B (12B, general purpose)"
  echo "           SicariusSicariiStuff/Wingless_Imp_8B (8B, roleplay/creative)"
  echo "  For 4bit: SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-64"
  echo "           SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-128"
  echo ""
  echo "Tool model options:"
  echo "  MadeAgents/Hammer2.1-1.5b"
  echo "  MadeAgents/Hammer2.1-3b"
  echo ""
  echo "Environment options:"
  echo "  CONCURRENT_MODEL_CALL=1  - Enable concurrent model calls (default: 0=sequential)"
  echo ""
  echo "Examples:"
  echo "  # Sequential mode (default)"
  echo "  $0 8bit SicariusSicariiStuff/Impish_Nemo_12B MadeAgents/Hammer2.1-1.5b"
  echo ""
  echo "  # 8B roleplay model"
  echo "  $0 8bit SicariusSicariiStuff/Wingless_Imp_8B MadeAgents/Hammer2.1-1.5b"
  echo ""
  echo "  # Concurrent mode for lower latency"
  echo "  CONCURRENT_MODEL_CALL=1 $0 8bit SicariusSicariiStuff/Impish_Nemo_12B MadeAgents/Hammer2.1-3b"
  echo ""
  echo "  # 4-bit with concurrent mode"
  echo "  CONCURRENT_MODEL_CALL=1 $0 4bit SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-64 MadeAgents/Hammer2.1-3b"
  exit 1
}

# Check if we have exactly 3 arguments
if [ $# -ne 3 ]; then
  log_warn "Error: Must specify quantization, chat model, and tool model"
  usage
fi

QUANT_TYPE="$1"
CHAT_MODEL_NAME="$2"
TOOL_MODEL_NAME="$3"

# Validate quantization type and chat model
case "${QUANT_TYPE}" in
  8bit)
    export QUANTIZATION=fp8
    if [ "${CHAT_MODEL_NAME}" != "SicariusSicariiStuff/Impish_Nemo_12B" ] && 
       [ "${CHAT_MODEL_NAME}" != "SicariusSicariiStuff/Wingless_Imp_8B" ]; then
      log_warn "Error: For 8bit quantization, must use one of:"
      log_warn "  SicariusSicariiStuff/Impish_Nemo_12B (12B, general purpose)"
      log_warn "  SicariusSicariiStuff/Wingless_Imp_8B (8B, roleplay/creative)"
      usage
    fi
    ;;
  4bit)
    export QUANTIZATION=gptq_marlin
    if [ "${CHAT_MODEL_NAME}" != "SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-64" ] && 
       [ "${CHAT_MODEL_NAME}" != "SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-128" ]; then
      log_warn "Error: For 4bit quantization, must use one of:"
      log_warn "  SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-64"
      log_warn "  SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-128"
      usage
    fi
    ;;
  *)
    log_warn "Error: Invalid quantization '${QUANT_TYPE}'. Must be '8bit' or '4bit'"
    usage
    ;;
esac

# Validate tool model
case "${TOOL_MODEL_NAME}" in
  MadeAgents/Hammer2.1-1.5b|MadeAgents/Hammer2.1-3b)
    # Valid tool model
    ;;
  *)
    log_warn "Error: Invalid tool model '${TOOL_MODEL_NAME}'. Must be one of:"
    log_warn "  MadeAgents/Hammer2.1-1.5b"
    log_warn "  MadeAgents/Hammer2.1-3b"
    usage
    ;;
esac

export CHAT_MODEL="${CHAT_MODEL_NAME}"
export TOOL_MODEL="${TOOL_MODEL_NAME}"

# Display configuration
CONCURRENT_STATUS="sequential (default)"
if [ "${CONCURRENT_MODEL_CALL:-0}" = "1" ]; then
  CONCURRENT_STATUS="concurrent (faster response)"
fi

log_info "Configuration: ${QUANT_TYPE} quantization"
log_info "  Chat model: ${CHAT_MODEL_NAME}"
log_info "  Tool model: ${TOOL_MODEL_NAME}"
log_info "  Model calls: ${CONCURRENT_STATUS}"

bash "${SCRIPT_DIR}/01_check_gpu.sh"
bash "${SCRIPT_DIR}/02_python_env.sh"
bash "${SCRIPT_DIR}/03_install_deps.sh"
source "${SCRIPT_DIR}/04_env_defaults.sh"
bash "${SCRIPT_DIR}/05_start_server.sh"
bash "${SCRIPT_DIR}/06_follow_logs.sh"


