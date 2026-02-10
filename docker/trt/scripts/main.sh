#!/usr/bin/env bash
# shellcheck disable=SC1091
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/logs.sh"

log_info "[main] Starting Yap Text Inference (TensorRT-LLM)..."

# Usage function
usage() {
  echo "Yap Text Inference Docker Container - TensorRT-LLM Engine"
  echo ""
  echo "This container is configured at build time with specific pre-quantized models."
  echo "TRT engines are downloaded from HuggingFace on first run and cached."
  echo ""
  echo "Required Environment Variables:"
  echo "  TEXT_API_KEY                    - API key for authentication (required)"
  echo ""
  echo "Optional Environment Variables:"
  echo "  HF_TOKEN                        - HuggingFace token (for private models/engines)"
  echo "  TRT_KV_FREE_GPU_FRAC            - GPU memory fraction for KV cache (default: 0.90)"
  echo ""
  echo "Note: CHAT_MODEL, TOOL_MODEL, and TRT_ENGINE_REPO are configured at build time."
  echo "      You don't need to specify them when running the container."
  echo ""
  echo "Example:"
  cat <<'EOF'
  docker run --gpus all -d \
    -e TEXT_API_KEY=your_secret_key \
    -p 8000:8000 IMAGE
EOF
  echo ""
  echo "With persistent cache (faster subsequent starts):"
  cat <<'EOF'
  docker run --gpus all -d \
    -v yap-cache:/app/.hf \
    -v yap-engines:/opt/engines \
    -e TEXT_API_KEY=your_secret_key \
    -p 8000:8000 IMAGE
EOF
  echo ""
  echo "Health check: curl http://localhost:8000/healthz"
  exit 0
}

# Check if help is requested
if [[ ${1:-} == "--help" ]] || [[ ${1:-} == "-h" ]]; then
  usage
fi

# Validate environment and set defaults
source "${SCRIPT_DIR}/bootstrap.sh"

if [ -z "${TEXT_API_KEY:-}" ]; then
  log_error "[main] ✗ TEXT_API_KEY is required"
  exit 1
fi

# Start the server

# Robust path resolution for start script
START_SCRIPT="${SCRIPT_DIR}/start_server.sh"
if [ ! -x "${START_SCRIPT}" ]; then
  log_error "[server] ✗ start_server.sh not found at ${START_SCRIPT}"
  ls -la "${SCRIPT_DIR}" || true
  exit 1
fi
exec "${START_SCRIPT}"
