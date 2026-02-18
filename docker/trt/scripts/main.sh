#!/usr/bin/env bash
# shellcheck disable=SC1091
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "/app/common/scripts/logs.sh"
source "/app/common/scripts/lifecycle.sh"

log_info "[main] Starting Yap Text Inference (TensorRT-LLM)..."

# Usage function
usage() {
  echo "Yap Text Inference Docker Container - TensorRT-LLM Engine"
  echo ""
  echo "This container is configured at build time with specific pre-quantized models."
  echo "TRT engines are baked into the image during build."
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

run_docker_main "trt" "${SCRIPT_DIR}" "usage" "script" "${SCRIPT_DIR}/start_server.sh" -- "$@"
