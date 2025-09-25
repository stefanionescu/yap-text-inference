#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

source "${SCRIPT_DIR}/utils.sh"

log_info "Starting Yap Text Inference Server"

# Usage function
usage() {
  echo "Usage: $0 <quantization> <model_name>"
  echo ""
  echo "Quantization options:"
  echo "  8bit  - Use 8-bit quantization (fp8)"
  echo "  4bit  - Use 4-bit quantization (GPTQ)"
  echo ""
  echo "Model options:"
  echo "  For 8bit: SicariusSicariiStuff/Impish_Nemo_12B"
  echo "  For 4bit: SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-64"
  echo "           SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-128"
  echo ""
  echo "Examples:"
  echo "  $0 8bit SicariusSicariiStuff/Impish_Nemo_12B"
  echo "  $0 4bit SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-64"
  echo "  $0 4bit SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-128"
  exit 1
}

# Check if we have exactly 2 arguments
if [ $# -ne 2 ]; then
  log_warn "Error: Must specify quantization and model name"
  usage
fi

QUANT_TYPE="$1"
MODEL_NAME="$2"

# Validate quantization type
case "${QUANT_TYPE}" in
  8bit)
    export QUANTIZATION=fp8
    if [ "${MODEL_NAME}" != "SicariusSicariiStuff/Impish_Nemo_12B" ]; then
      log_warn "Error: For 8bit quantization, must use: SicariusSicariiStuff/Impish_Nemo_12B"
      usage
    fi
    ;;
  4bit)
    export QUANTIZATION=gptq_marlin
    if [ "${MODEL_NAME}" != "SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-64" ] && 
       [ "${MODEL_NAME}" != "SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-128" ]; then
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

export CHAT_MODEL="${MODEL_NAME}"
log_info "Configuration: ${QUANT_TYPE} quantization with model ${MODEL_NAME}"

bash "${SCRIPT_DIR}/01_check_gpu.sh"
bash "${SCRIPT_DIR}/02_python_env.sh"
bash "${SCRIPT_DIR}/03_install_deps.sh"
source "${SCRIPT_DIR}/04_env_defaults.sh"
bash "${SCRIPT_DIR}/05_start_server.sh"
bash "${SCRIPT_DIR}/06_follow_logs.sh"


