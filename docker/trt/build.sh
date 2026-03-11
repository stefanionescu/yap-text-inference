#!/usr/bin/env bash
# shellcheck disable=SC1091
set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC2034  # sourced helper scripts rely on ROOT_DIR
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
COMMON_DIR="${SCRIPT_DIR}/../common"
source "${COMMON_DIR}/scripts/build/defaults.sh"
build_init_trt_defaults

# Deploy mode: chat|both (tool-only is handled by docker/tool/build.sh)
case "${DEPLOY_MODE_VAL}" in
  chat | both) ;;
  tool)
    if [[ ${1:-} != "--help" ]]; then
      echo "[build] DEPLOY_MODE=tool is not supported in docker/trt/build.sh" >&2
      echo "[build] Use docker/tool/build.sh or docker/build.sh with DEPLOY_MODE=tool" >&2
      exit 1
    fi
    ;;
  *)
    echo "[build] Invalid DEPLOY_MODE='${DEPLOY_MODE_VAL}'. Must be 'chat' or 'both'" >&2
    exit 1
    ;;
esac

# Validate tag naming convention
if [[ ! ${TAG} =~ ^trt- ]]; then
  echo "[build] ✗ TAG must start with 'trt-' for TensorRT images" >&2
  echo "[build]   Got: ${TAG}" >&2
  echo "[build]   Example: trt-qwen30b-sm90" >&2
  exit 1
fi

# shellcheck disable=SC2034  # Used by sourced scripts
DOCKERFILE="${SCRIPT_DIR}/Dockerfile"

# Modules - shared utilities from common
source "${COMMON_DIR}/scripts/logs.sh"
source "${COMMON_DIR}/scripts/build/driver.sh"

# Usage function
usage() {
  echo "Usage: $0 [OPTIONS]"
  echo ""
  echo "Build and push Yap Text Inference Docker image (TensorRT-LLM engine)"
  echo ""
  echo "IMPORTANT: The pre-built TRT engine is BAKED INTO the image at build time."
  echo "           When you run the container, the engine is already there - just start and go!"
  echo ""
  echo "Environment Variables:"
  echo "  DOCKER_USERNAME     - Docker Hub username (required)"
  echo "  IMAGE_NAME          - Docker image name (default: yap-text-api)"
  echo "  DEPLOY_MODE         - chat|both (default: both)"
  echo "  CHAT_MODEL          - HuggingFace TRT-quantized model repo (required for chat/both)"
  echo "                        This repo contains the checkpoint for tokenizer"
  echo "  TRT_ENGINE_REPO     - HuggingFace repo with pre-built TRT engines (defaults to CHAT_MODEL)"
  echo "  TRT_ENGINE_LABEL    - Engine directory name in the repo (required for chat/both)"
  echo "                        Format: sm{arch}_trt-llm-{version}_cuda{version}"
  echo "                        Example: sm90_trt-llm-0.17.0_cuda12.8"
  echo "  TOOL_MODEL          - Tool model HF repo (required for both)"
  echo "  TAG                 - Image tag (MUST start with 'trt-')"
  echo "  PLATFORM            - Target platform (default: linux/amd64)"
  echo "  HF_TOKEN            - HuggingFace token (for private repos)"
  echo "  NO_CACHE            - Build without Docker cache (default: 0)"
  echo ""
  echo "  Note: For tool-only images, use docker/tool/build.sh"
  echo ""
  echo "Options:"
  echo "  --help              - Show this help message"
  echo ""
  echo "Examples:"
  cat <<'EOF'
  # Build chat-only image with pre-built engine baked in
  DOCKER_USERNAME=myuser \
    DEPLOY_MODE=chat \
    CHAT_MODEL=yapwithai/qwen3-30b-trt-awq \
    TRT_ENGINE_LABEL=sm90_trt-llm-0.17.0_cuda12.8 \
    TAG=trt-qwen30b-sm90 \
    ./build.sh

  # Build both models
  DOCKER_USERNAME=myuser \
    DEPLOY_MODE=both \
    CHAT_MODEL=yapwithai/qwen3-30b-trt-awq \
    TRT_ENGINE_LABEL=sm90_trt-llm-0.17.0_cuda12.8 \
    TOOL_MODEL=yapwithai/yap-modernbert-screenshot-intent \
    TAG=trt-qwen3-full-sm90 \
    ./build.sh
EOF
  echo ""
  echo "Running the built image:"
  echo "  docker run -d --gpus all -e TEXT_API_KEY=xxx -p 8000:8000 myuser/yap-text-api:TAG"
  exit 0
}

# No command-line flags supported except --help
if [[ ${1-} == "--help" ]]; then
  usage
fi

validate_tag_prefix "${TAG}" "trt-" "TensorRT" "trt-qwen30b-sm90"

# validate_stack_build - Run shared model and engine validation for the TRT stack.
validate_stack_build() {
  log_info "[build] Validating configuration for DEPLOY_MODE=${DEPLOY_MODE_VAL}..."
  if ! validate_models_for_deploy_common \
    "trt" \
    "${DEPLOY_MODE_VAL}" \
    "${CHAT_MODEL}" \
    "${TOOL_MODEL}" \
    "${TRT_ENGINE_REPO}" \
    "${TRT_ENGINE_LABEL}"; then
    log_err "[build] ✗ Configuration validation failed. Build aborted."
    exit 1
  fi
}

# log_stack_build - Print the TRT-specific build summary before docker build.
log_stack_build() {
  log_info "[build] Pre-built engine will be baked into the image"
}

# append_stack_build_args - Add TRT-specific build arguments to BUILD_ARGS.
append_stack_build_args() {
  BUILD_ARGS+=(--build-arg "DEPLOY_MODE=${DEPLOY_MODE_VAL}")
  [[ -n ${CHAT_MODEL} ]] && BUILD_ARGS+=(--build-arg "CHAT_MODEL=${CHAT_MODEL}")
  [[ -n ${TOOL_MODEL} ]] && BUILD_ARGS+=(--build-arg "TOOL_MODEL=${TOOL_MODEL}")
  [[ -n ${TRT_ENGINE_REPO} ]] && BUILD_ARGS+=(--build-arg "TRT_ENGINE_REPO=${TRT_ENGINE_REPO}")
  [[ -n ${TRT_ENGINE_LABEL} ]] && BUILD_ARGS+=(--build-arg "TRT_ENGINE_LABEL=${TRT_ENGINE_LABEL}")
  [[ -n ${CHAT_QUANTIZATION} ]] && BUILD_ARGS+=(--build-arg "CHAT_QUANTIZATION=${CHAT_QUANTIZATION}")
  [[ -n ${HF_TOKEN} ]] && BUILD_ARGS+=(--secret "id=hf_token,env=HF_TOKEN")
}

run_stack_build "${SCRIPT_DIR}" "requirements-trt.txt" "1" "yap-trt"
