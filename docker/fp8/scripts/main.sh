#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common/utils.sh"

log_info "Starting Yap Text Inference Docker Container (FP8/GPTQ Auto)"

usage() {
  echo "Yap Text Inference Docker Container - FP8/GPTQ Auto-Quantization"
  echo ""
  echo "This container supports float or GPTQ models from Hugging Face."
  echo "Quantization is auto-detected: GPTQ if chat model name contains 'GPTQ', else FP8."
  echo ""
  echo "Required Environment Variables:"
  echo "  CHAT_MODEL  - Hugging Face repo for chat model (float or GPTQ)"
  echo "  TOOL_MODEL  - Hugging Face repo for tool model (float or GPTQ)"
  echo ""
  echo "Optional Environment Variables:"
  echo "  YAP_TEXT_API_KEY           - API key for authentication (default: yap_token)"
  echo "  DEPLOY_MODELS=both|chat|tool - Which models to deploy (default: both)"
  echo "  CONCURRENT_MODEL_CALL=0|1  - Concurrent model calls (default: 1)"
  echo "  KV_DTYPE=auto|fp8|int8     - KV cache dtype (auto-set by env)"
  echo "  QUANTIZATION=auto|fp8|gptq_marlin - Override auto detection"
  echo ""
  echo "Examples:"
  echo "  docker run -d --gpus all --name yap-server \\
    -e CHAT_MODEL=your-org/chat-float \\
    -e TOOL_MODEL=your-org/tool-float \\
    yourusername/yap-text-inference-auto:latest"
  echo ""
  echo "  docker run -d --gpus all --name yap-server \\
    -e CHAT_MODEL=SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-64 \\
    -e TOOL_MODEL=MadeAgents/Hammer2.1-3b \\
    yourusername/yap-text-inference-auto:latest"
  echo ""
  echo "Health check: curl http://localhost:8000/healthz"
  exit 0
}

if [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]]; then
  usage
fi

# Load and validate environment
source "${SCRIPT_DIR}/common/env.sh"

log_info ""
log_info "=== FP8/GPTQ Docker Deployment Configuration ==="
log_info "Deploy mode: ${DEPLOY_MODELS}"
log_info "Chat model: ${CHAT_MODEL:-none}"
log_info "Tool model: ${TOOL_MODEL:-none}"
log_info "Concurrent calls: ${CONCURRENT_MODEL_CALL}"
log_info "GPU: ${DETECTED_GPU_NAME:-unknown}"
log_info "API Key: ${YAP_TEXT_API_KEY:-yap_token}"
log_info "==============================================="
log_info ""

log_info "Starting server..."
exec "${SCRIPT_DIR}/start_server.sh"


