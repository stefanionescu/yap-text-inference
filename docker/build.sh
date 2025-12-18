#!/usr/bin/env bash
set -euo pipefail

# Unified Docker build script for Yap Text Inference
# Supports both vLLM and TensorRT-LLM engines

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Engine selection: vllm (default) or trt
ENGINE="${ENGINE:-vllm}"

# Validate engine selection
case "${ENGINE}" in
  vllm|trt) ;;
  *)
    echo "[build] Invalid ENGINE='${ENGINE}'. Must be 'vllm' or 'trt'" >&2
    exit 1
    ;;
esac

# Usage function
usage() {
    echo "Usage: ENGINE=<vllm|trt> $0 [OPTIONS]"
    echo ""
    echo "Unified build script for Yap Text Inference Docker images"
    echo ""
    echo "Engine Selection (required):"
    echo "  ENGINE=vllm         - Build vLLM-based image (default)"
    echo "  ENGINE=trt          - Build TensorRT-LLM-based image"
    echo ""
    echo "Common Environment Variables:"
    echo "  DOCKER_USERNAME     - Docker Hub username (required)"
    echo "  IMAGE_NAME          - Docker image name (default: yap-text-api)"
    echo "  DEPLOY_MODELS       - chat|tool|both (default: both)"
    echo "  CHAT_MODEL          - Chat model HF repo (required for chat/both)"
    echo "  TOOL_MODEL          - Tool classifier HF repo (required for tool/both)"
    echo "  TAG                 - Custom image tag"
    echo "  PLATFORM            - Target platform (default: linux/amd64)"
    echo ""
    echo "vLLM-specific:"
    echo "  CHAT_MODEL must be pre-quantized (AWQ/GPTQ/W4A16)"
    echo ""
    echo "TRT-specific:"
    echo "  TRT_ENGINE_REPO     - HF repo with pre-built TRT engines"
    echo "                        (or leave empty for mounted engines)"
    echo ""
    echo "Examples:"
    echo ""
    echo "  # vLLM chat-only"
    echo "  ENGINE=vllm DOCKER_USERNAME=myuser \\"
    echo "    DEPLOY_MODELS=chat \\"
    echo "    CHAT_MODEL=cpatonn/Qwen3-30B-A3B-Instruct-2507-AWQ-4bit \\"
    echo "    TAG=vllm-qwen30b \\"
    echo "    ./docker/build.sh"
    echo ""
    echo "  # TRT-LLM chat-only"
    echo "  ENGINE=trt DOCKER_USERNAME=myuser \\"
    echo "    DEPLOY_MODELS=chat \\"
    echo "    CHAT_MODEL=Qwen/Qwen3-30B-A3B \\"
    echo "    TRT_ENGINE_REPO=myuser/qwen3-30b-trt-engine \\"
    echo "    TAG=trt-qwen30b \\"
    echo "    ./docker/build.sh"
    echo ""
    exit 0
}

# Check for help flag
if [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]]; then
    usage
fi

# Delegate to engine-specific build script
ENGINE_BUILD_SCRIPT="${SCRIPT_DIR}/${ENGINE}/build.sh"

if [[ ! -f "${ENGINE_BUILD_SCRIPT}" ]]; then
    echo "[build] Build script not found: ${ENGINE_BUILD_SCRIPT}" >&2
    exit 1
fi

echo "[build] Building with engine: ${ENGINE}"
echo "[build] Delegating to: ${ENGINE_BUILD_SCRIPT}"
echo ""

exec "${ENGINE_BUILD_SCRIPT}" "$@"
