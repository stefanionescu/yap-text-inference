#!/usr/bin/env bash
set -euo pipefail

# Unified Docker build script for Yap Text Inference
# Supports both vLLM and TensorRT-LLM engines
#
# IMPORTANT: All images are pre-baked with models/engines at build time.
# - TRT images: Require TRT_ENGINE_REPO and TRT_ENGINE_LABEL to specify the exact engine
# - vLLM images: Require pre-quantized CHAT_MODEL (AWQ/GPTQ/W4A16)
#
# Tags MUST follow naming convention: trt-* or vllm-*

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

# Validate tag naming convention
TAG="${TAG:-}"
if [[ -n "${TAG}" ]]; then
  case "${ENGINE}" in
    trt)
      if [[ ! "${TAG}" =~ ^trt- ]]; then
        echo "[build] ✗ TAG must start with 'trt-' for TensorRT images" >&2
        echo "[build]   Got: ${TAG}" >&2
        echo "[build]   Example: trt-qwen30b-sm90" >&2
        exit 1
      fi
      ;;
    vllm)
      if [[ ! "${TAG}" =~ ^vllm- ]]; then
        echo "[build] ✗ TAG must start with 'vllm-' for vLLM images" >&2
        echo "[build]   Got: ${TAG}" >&2
        echo "[build]   Example: vllm-qwen30b-awq" >&2
        exit 1
      fi
      ;;
  esac
fi

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
    echo "  DEPLOY_MODE         - chat|tool|both (default: both)"
    echo "  CHAT_MODEL          - Chat model HF repo (required for chat/both)"
    echo "  TOOL_MODEL          - Tool classifier HF repo (required for tool/both)"
    echo "  TAG                 - Image tag (MUST start with 'trt-' or 'vllm-')"
    echo "  PLATFORM            - Target platform (default: linux/amd64)"
    echo "  HF_TOKEN            - HuggingFace token (required for private repos)"
    echo ""
    echo "vLLM-specific (pre-quantized models baked into image):"
    echo "  CHAT_MODEL          - Must be pre-quantized (AWQ/GPTQ/W4A16)"
    echo "                        The entire model is downloaded at build time"
    echo ""
    echo "TRT-specific (pre-built engines baked into image):"
    echo "  TRT_ENGINE_REPO     - HF repo with pre-built TRT engines (defaults to CHAT_MODEL)"
    echo "  TRT_ENGINE_LABEL    - Engine directory name in the repo (required)"
    echo "                        Format: sm{arch}_trt-llm-{version}_cuda{version}"
    echo "                        Example: sm90_trt-llm-1.2.0rc5_cuda13.0"
    echo ""
    echo "Examples:"
    echo ""
    echo "  # vLLM: Pre-quantized AWQ model baked into image"
    echo "  ENGINE=vllm DOCKER_USERNAME=myuser \\"
    echo "    DEPLOY_MODE=chat \\"
    echo "    CHAT_MODEL=cpatonn/Qwen3-30B-A3B-Instruct-2507-AWQ-4bit \\"
    echo "    TAG=vllm-qwen30b-awq \\"
    echo "    ./docker/build.sh"
    echo ""
    echo "  # TRT: Pre-built engine baked into image"
    echo "  ENGINE=trt DOCKER_USERNAME=myuser \\"
    echo "    DEPLOY_MODE=chat \\"
    echo "    CHAT_MODEL=yapwithai/qwen3-30b-trt-awq \\"
    echo "    TRT_ENGINE_LABEL=sm90_trt-llm-0.17.0_cuda12.8 \\"
    echo "    TAG=trt-qwen30b-sm90 \\"
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
