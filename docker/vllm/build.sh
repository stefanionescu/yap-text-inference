#!/usr/bin/env bash
# shellcheck disable=SC1091
set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC2034  # sourced helper scripts rely on ROOT_DIR
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
COMMON_DIR="${SCRIPT_DIR}/../common"
source "${COMMON_DIR}/scripts/build/defaults.sh"
build_init_vllm_defaults

# Deploy mode: chat|both (tool-only is handled by docker/tool/build.sh)
case "${DEPLOY_MODE_VAL}" in
  chat | both) ;;
  tool)
    if [[ ${1:-} != "--help" ]]; then
      echo "[build] DEPLOY_MODE=tool is not supported in docker/vllm/build.sh" >&2
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
if [[ ! ${TAG} =~ ^vllm- ]]; then
  echo "[build] ✗ TAG must start with 'vllm-' for vLLM images" >&2
  echo "[build]   Got: ${TAG}" >&2
  echo "[build]   Example: vllm-qwen30b-awq" >&2
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
  echo "Build and push Yap Text Inference Docker image (vLLM engine)"
  echo ""
  echo "IMPORTANT: The pre-quantized model is BAKED INTO the image at build time."
  echo "           When you run the container, the model is already there - just start and go!"
  echo ""
  echo "Environment Variables:"
  echo "  DOCKER_USERNAME     - Docker Hub username (required)"
  echo "  IMAGE_NAME          - Docker image name (default: yap-text-api)"
  echo "  DEPLOY_MODE         - chat|both (default: both)"
  echo "  CHAT_MODEL          - Pre-quantized chat model HF repo (required for chat/both)"
  echo "                        Name should contain awq/gptq/fp8, or config.json must declare quant_method"
  echo "  TOOL_MODEL          - Tool model HF repo (required for both)"
  echo "  TAG                 - Image tag (MUST start with 'vllm-')"
  echo "  HF_TOKEN            - HuggingFace token (for private repos)"
  echo "  NO_CACHE            - Build without Docker cache (default: 0)"
  echo ""
  echo "Build platform is fixed to linux/amd64."
  echo ""
  echo "  Note: For tool-only images, use docker/tool/build.sh"
  echo ""
  echo "Options:"
  echo "  --help              - Show this help message"
  echo ""
  echo "Examples:"
  cat <<'EOF'
  # Build chat-only image with pre-quantized model baked in
  DOCKER_USERNAME=myuser \
    DEPLOY_MODE=chat \
    CHAT_MODEL=cpatonn/Qwen3-30B-A3B-Instruct-2507-AWQ-4bit \
    TAG=vllm-qwen30b-awq \
    ./build.sh

  # Build both models
  DOCKER_USERNAME=myuser \
    DEPLOY_MODE=both \
    CHAT_MODEL=cpatonn/Qwen3-30B-A3B-Instruct-2507-AWQ-4bit \
    TOOL_MODEL=yapwithai/yap-modernbert-screenshot-intent \
    TAG=vllm-qwen3-full \
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

validate_tag_prefix "${TAG}" "vllm-" "vLLM" "vllm-qwen30b-awq"

# validate_stack_build - Run shared model validation for the vLLM stack.
validate_stack_build() {
  log_info "[build] Validating models for DEPLOY_MODE=${DEPLOY_MODE_VAL}..."
  if ! validate_models_for_deploy_common "vllm" "${DEPLOY_MODE_VAL}" "${CHAT_MODEL}" "${TOOL_MODEL}"; then
    log_err "[build] ✗ Model validation failed. Build aborted."
    exit 1
  fi
}

# log_stack_build - Print the vLLM-specific build summary before docker build.
log_stack_build() {
  log_info "[build] Pre-quantized model will be baked into the image"
  if [[ -n ${CHAT_MODEL} ]]; then
    log_info "[build]   Chat model: ${CHAT_MODEL}"
  fi
  if [[ -n ${TOOL_MODEL} ]]; then
    log_info "[build]   Tool model: ${TOOL_MODEL}"
  fi
}

# append_stack_build_args - Add vLLM-specific build arguments to BUILD_ARGS.
append_stack_build_args() {
  BUILD_ARGS+=(--build-arg "DEPLOY_MODE=${DEPLOY_MODE_VAL}")
  [[ -n ${CHAT_MODEL} ]] && BUILD_ARGS+=(--build-arg "CHAT_MODEL=${CHAT_MODEL}")
  [[ -n ${TOOL_MODEL} ]] && BUILD_ARGS+=(--build-arg "TOOL_MODEL=${TOOL_MODEL}")
  [[ -n ${CHAT_QUANTIZATION} ]] && BUILD_ARGS+=(--build-arg "CHAT_QUANTIZATION=${CHAT_QUANTIZATION}")
  [[ -n ${HF_TOKEN} ]] && BUILD_ARGS+=(--secret "id=hf_token,env=HF_TOKEN")
}

run_stack_build "${SCRIPT_DIR}" "requirements-vllm.txt" "1" "yap-vllm"
