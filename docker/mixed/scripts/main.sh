#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/logs.sh"

log_info "Starting Yap Text Inference Docker Container (Base)"

usage() {
  echo "Yap Text Inference Docker Container - Base Image"
  echo ""
  echo "This image embeds models at build time and runs them as-is:"
  echo "  - Pre-quantized AWQ models (chat and/or tool)"
  echo "  - Float models (run with fp8 path where applicable)"
  echo ""
  echo "Models are preloaded during docker build; runtime does not download or quantize."
  echo ""
  echo "Runtime knobs:"
  echo "  DEPLOY_MODELS=both|chat|tool     (default: both if both embedded)"
  echo ""
  echo "Examples:"
  echo "  docker run -d --gpus all IMAGE"
  echo "  docker run -d --gpus all -e DEPLOY_MODELS=chat IMAGE"
  echo ""
  echo "Health: curl http://localhost:8000/healthz"
  exit 0
}

if [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]]; then
  usage
fi

# Load env and decide quantization choices
source "${SCRIPT_DIR}/bootstrap.sh"

log_info "Starting server..."
exec "${SCRIPT_DIR}/start_server.sh"


