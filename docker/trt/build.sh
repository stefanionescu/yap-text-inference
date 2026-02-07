#!/usr/bin/env bash
set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC2034  # sourced helper scripts rely on ROOT_DIR
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Docker configuration
DOCKER_USERNAME="${DOCKER_USERNAME:-your-username}"
IMAGE_NAME="${IMAGE_NAME:-yap-text-api}"

# Deploy mode: chat|tool|both
DEPLOY_MODE_VAL="${DEPLOY_MODE:-both}"
case "${DEPLOY_MODE_VAL}" in
  chat | tool | both) ;;
  *)
    echo "[build] Invalid DEPLOY_MODE='${DEPLOY_MODE_VAL}', defaulting to 'both'" >&2
    DEPLOY_MODE_VAL="both"
    ;;
esac

# Model configuration (required based on DEPLOY_MODE)
CHAT_MODEL="${CHAT_MODEL:-}"
TOOL_MODEL="${TOOL_MODEL:-}"
CHAT_QUANTIZATION="${CHAT_QUANTIZATION:-}"

# TRT Engine configuration (REQUIRED for chat/both modes)
# TRT_ENGINE_REPO: HuggingFace repo containing pre-built TRT engines (defaults to CHAT_MODEL)
# TRT_ENGINE_LABEL: Engine directory name (e.g., sm90_trt-llm-0.17.0_cuda12.8)
TRT_ENGINE_REPO="${TRT_ENGINE_REPO:-${CHAT_MODEL}}"
TRT_ENGINE_LABEL="${TRT_ENGINE_LABEL:-}"

# HuggingFace token for private repos
HF_TOKEN="${HF_TOKEN:-}"

# Custom tag (MUST start with trt-)
TAG="${TAG:-trt-${DEPLOY_MODE_VAL}}"

# Validate tag naming convention
if [[ ! ${TAG} =~ ^trt- ]]; then
  echo "[build] ✗ TAG must start with 'trt-' for TensorRT images" >&2
  echo "[build]   Got: ${TAG}" >&2
  echo "[build]   Example: trt-qwen30b-sm90" >&2
  exit 1
fi

FULL_IMAGE_NAME="${DOCKER_USERNAME}/${IMAGE_NAME}:${TAG}"

# Build configuration
PLATFORM="${PLATFORM:-linux/amd64}"
# Use stack directory as primary build context so its local .dockerignore applies
BUILD_CONTEXT="${SCRIPT_DIR}"
# shellcheck disable=SC2034  # Used by sourced scripts
DOCKERFILE="${SCRIPT_DIR}/Dockerfile"

# Modules - shared utilities from common, engine-specific from local
COMMON_DIR="${SCRIPT_DIR}/../common"
source "${COMMON_DIR}/scripts/logs.sh"
source "${COMMON_DIR}/scripts/build/docker.sh"
source "${COMMON_DIR}/scripts/build/args.sh"
source "${SCRIPT_DIR}/scripts/build/context.sh"
source "${SCRIPT_DIR}/scripts/build/validate.sh"

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
  echo "  DEPLOY_MODE         - chat|tool|both (default: both)"
  echo "  CHAT_MODEL          - HuggingFace TRT-quantized model repo (required for chat/both)"
  echo "                        This repo contains the checkpoint for tokenizer"
  echo "  TRT_ENGINE_REPO     - HuggingFace repo with pre-built TRT engines (defaults to CHAT_MODEL)"
  echo "  TRT_ENGINE_LABEL    - Engine directory name in the repo (required for chat/both)"
  echo "                        Format: sm{arch}_trt-llm-{version}_cuda{version}"
  echo "                        Example: sm90_trt-llm-0.17.0_cuda12.8"
  echo "  TOOL_MODEL          - Tool classifier model HF repo (required for tool/both)"
  echo "  TAG                 - Image tag (MUST start with 'trt-')"
  echo "  PLATFORM            - Target platform (default: linux/amd64)"
  echo "  HF_TOKEN            - HuggingFace token (for private repos)"
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

  # Build tool-only image
  DOCKER_USERNAME=myuser \
    DEPLOY_MODE=tool \
    TOOL_MODEL=yapwithai/yap-modernbert-screenshot-intent \
    TAG=trt-tool-only \
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
if [[ ${1:-} == "--help" ]]; then
  usage
fi

# Validate configuration
if [[ ${DOCKER_USERNAME} == "your-username" ]]; then
  log_error "[build] ✗ Please set DOCKER_USERNAME environment variable"
  log_info "[build] Example: DOCKER_USERNAME=myuser $0"
  exit 1
fi

# Validate models and engine configuration
log_info "[build] Validating configuration for DEPLOY_MODE=${DEPLOY_MODE_VAL}..."
if ! validate_models_for_deploy "${DEPLOY_MODE_VAL}" "${CHAT_MODEL}" "${TOOL_MODEL}" "${TRT_ENGINE_REPO}" "${TRT_ENGINE_LABEL}"; then
  log_error "[build] ✗ Configuration validation failed. Build aborted."
  exit 1
fi
echo # blank line after validation

require_docker

ensure_docker_login

log_info "[build] Building Docker image..."
log_info "[build] Pre-built engine will be baked into the image"

# Build the image
prepare_build_context
init_build_args

# Add model build args - these become ENV vars in the image
BUILD_ARGS+=(--build-arg "DEPLOY_MODE=${DEPLOY_MODE_VAL}")
[[ -n ${CHAT_MODEL} ]] && BUILD_ARGS+=(--build-arg "CHAT_MODEL=${CHAT_MODEL}")
[[ -n ${TOOL_MODEL} ]] && BUILD_ARGS+=(--build-arg "TOOL_MODEL=${TOOL_MODEL}")
[[ -n ${TRT_ENGINE_REPO} ]] && BUILD_ARGS+=(--build-arg "TRT_ENGINE_REPO=${TRT_ENGINE_REPO}")
[[ -n ${TRT_ENGINE_LABEL} ]] && BUILD_ARGS+=(--build-arg "TRT_ENGINE_LABEL=${TRT_ENGINE_LABEL}")
[[ -n ${CHAT_QUANTIZATION} ]] && BUILD_ARGS+=(--build-arg "CHAT_QUANTIZATION=${CHAT_QUANTIZATION}")

# Pass HF_TOKEN as a secret (not a build arg) so it's not baked into the image
[[ -n ${HF_TOKEN} ]] && BUILD_ARGS+=(--secret "id=hf_token,env=HF_TOKEN")

docker build "${BUILD_ARGS[@]}" "${BUILD_CONTEXT}"

log_success "[build] ✓ Docker build complete"
log_info "[build] Pushing to Docker Hub..."

# Try push; if unauthorized, attempt non-interactive login and retry once
if ! docker push "${FULL_IMAGE_NAME}"; then
  log_warn "[build] ⚠ Initial docker push failed. Attempting non-interactive login and retry..."
  ensure_docker_login || true
  if ! docker push "${FULL_IMAGE_NAME}"; then
    log_error "[build] ✗ Docker push failed. Please run 'docker login' and ensure DOCKER_USERNAME has access to push ${FULL_IMAGE_NAME}."
    exit 1
  fi
fi

log_success "[build] ✓ Pushed"
