#!/usr/bin/env bash
# shellcheck disable=SC1091
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "/app/common/scripts/logs.sh"
source "/app/common/scripts/lifecycle.sh"

log_info "[main] Starting Yap Text Inference (Tool-Only)..."

# Usage function
usage() {
  echo "Yap Text Inference Docker Container - Tool-Only"
  echo ""
  echo "This container is configured at build time with a tool model."
  echo "No chat engine is included -- lightweight deployment."
  echo ""
  echo "Required Environment Variables:"
  echo "  TEXT_API_KEY                    - API key for authentication (required)"
  echo ""
  echo "Optional Environment Variables:"
  echo "  HF_TOKEN                        - HuggingFace token (for private models)"
  echo "  TOOL_GPU_FRAC                   - GPU memory fraction for tool model"
  echo ""
  echo "Note: TOOL_MODEL is configured at build time."
  echo "      You don't need to specify it when running the container."
  echo ""
  echo "Example:"
  cat <<'EOF'
  docker run --gpus all -d \
    -e TEXT_API_KEY=your_secret_key \
    -p 8000:8000 IMAGE
EOF
  echo ""
  echo "Health check: curl http://localhost:8000/healthz"
  exit 0
}

run_docker_main "tool" "${SCRIPT_DIR}" "usage" "direct_common" -- "$@"
