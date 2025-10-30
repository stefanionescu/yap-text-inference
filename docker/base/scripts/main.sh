#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/logs.sh"

log_info "Starting Yap Text Inference Docker Container (Base)"

usage() {
  echo "Yap Text Inference Docker Container - Base Image"
  echo ""
  echo "Supports the following scenarios at build time and run time:"
  echo "  - Pre-quantized AWQ models (chat and/or tool)"
  echo "  - Float/GPTQ models (chat and/or tool)"
  echo "  - Optional runtime AWQ quantization for float models"
  echo ""
  echo "Required (depending on DEPLOY_MODELS):"
  echo "  CHAT_MODEL               - HF repo or local path (float/GPTQ)"
  echo "  TOOL_MODEL               - HF repo or local path (float/GPTQ)"
  echo "  or AWQ_CHAT_MODEL / AWQ_TOOL_MODEL for pre-quantized AWQ"
  echo ""
  echo "Optional runtime knobs:"
  echo "  DEPLOY_MODELS=both|chat|tool     (default: both)"
  echo "  QUANTIZATION=auto|fp8|gptq_marlin|awq (default: auto)"
  echo "  CONCURRENT_MODEL_CALL=0|1        (default: 1 concurrent)"
  echo "  HF_AWQ_PUSH=0|1 + HF_TOKEN + HF_AWQ_* for post-quant push"
  echo ""
  echo "Examples:"
  echo "  # Pre-quantized AWQ both"
  echo "  docker run -d --gpus all -e AWQ_CHAT_MODEL=your-org/chat-awq -e AWQ_TOOL_MODEL=your-org/tool-awq IMAGE"
  echo ""
  echo "  # Chat AWQ + Tool float"
  echo "  docker run -d --gpus all -e AWQ_CHAT_MODEL=your-org/chat-awq -e TOOL_MODEL=MadeAgents/Hammer2.1-3b IMAGE"
  echo ""
  echo "  # Float/GPTQ, no quantization (auto-detect GPTQ by name)"
  echo "  docker run -d --gpus all -e CHAT_MODEL=SicariusSicariiStuff/Impish_Nemo_12B -e TOOL_MODEL=MadeAgents/Hammer2.1-3b IMAGE"
  echo ""
  echo "  # Quantize both to AWQ at runtime and push to HF"
  echo "  docker run -d --gpus all -e QUANTIZATION=awq -e CHAT_MODEL=SicariusSicariiStuff/Impish_Nemo_12B -e TOOL_MODEL=MadeAgents/Hammer2.1-3b -e HF_AWQ_PUSH=1 -e HF_TOKEN=hf_xxx -e HF_AWQ_CHAT_REPO=org/chat-awq -e HF_AWQ_TOOL_REPO=org/tool-awq IMAGE"
  echo ""
  echo "Health: curl http://localhost:8000/healthz"
  exit 0
}

if [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]]; then
  usage
fi

# Load env and decide quantization choices
source "${SCRIPT_DIR}/bootstrap.sh"

# If QUANTIZATION=awq, run optional local quantization unless pre-quantized models are already provided
if [ "${QUANTIZATION}" = "awq" ]; then
  source "${SCRIPT_DIR}/quantization/quantizer.sh"
fi

log_info "Starting server..."
exec "${SCRIPT_DIR}/start_server.sh"


