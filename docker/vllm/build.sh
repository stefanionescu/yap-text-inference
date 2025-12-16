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
DEPLOY_MODELS_VAL="${DEPLOY_MODELS:-both}"
case "${DEPLOY_MODELS_VAL}" in
  chat|tool|both) ;;
  *)
    echo "[WARN] Invalid DEPLOY_MODELS='${DEPLOY_MODELS_VAL}', defaulting to 'both'" >&2
    DEPLOY_MODELS_VAL="both"
    ;;
esac

# Model configuration (required based on DEPLOY_MODELS)
CHAT_MODEL="${CHAT_MODEL:-}"
TOOL_MODEL="${TOOL_MODEL:-}"

# Custom tag (optional - defaults to vllm-deploy mode if not set)
TAG="${TAG:-vllm-${DEPLOY_MODELS_VAL}}"
FULL_IMAGE_NAME="${DOCKER_USERNAME}/${IMAGE_NAME}:${TAG}"

# Build configuration
PLATFORM="${PLATFORM:-linux/amd64}"
# Use stack directory as primary build context so its local .dockerignore applies
BUILD_CONTEXT="${SCRIPT_DIR}"
DOCKERFILE="${SCRIPT_DIR}/Dockerfile"

# Modules
source "${SCRIPT_DIR}/scripts/build/logs.sh"
source "${SCRIPT_DIR}/scripts/build/docker.sh"
source "${SCRIPT_DIR}/scripts/build/args.sh"
source "${SCRIPT_DIR}/scripts/build/context.sh"
source "${SCRIPT_DIR}/scripts/build/validate.sh"

# Usage function
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Build and push Yap Text Inference Docker image (vLLM engine)"
    echo ""
    echo "The image is configured at build time with specific pre-quantized models."
    echo "When run, the container automatically downloads those models from HuggingFace."
    echo ""
    echo "Environment Variables:"
    echo "  DOCKER_USERNAME     - Docker Hub username (required)"
    echo "  IMAGE_NAME          - Docker image name (default: yap-text-api)"
    echo "  DEPLOY_MODELS       - chat|tool|both (default: both)"
    echo "  CHAT_MODEL          - Pre-quantized chat model HF repo (required for chat/both)"
    echo "                        Must contain: awq, gptq, w4a16, nvfp4, compressed-tensors, or autoround"
    echo "  TOOL_MODEL          - Tool classifier model HF repo (required for tool/both)"
    echo "                        Must be in the allowlist (see src/config/models.py)"
    echo "  TAG                 - Custom image tag (default: vllm-<DEPLOY_MODELS>)"
    echo "  PLATFORM            - Target platform (default: linux/amd64)"
    echo ""
    echo "Options:"
    echo "  --help              - Show this help message"
    echo ""
    echo "Examples:"
    echo "  # Build chat-only image"
    echo "  DOCKER_USERNAME=myuser \\"
    echo "    DEPLOY_MODELS=chat \\"
    echo "    CHAT_MODEL=jeffcookio/Mistral-Small-3.2-24B-Instruct-2506-awq-sym \\"
    echo "    TAG=vllm-mistral-24b \\"
    echo "    ./build.sh"
    echo ""
    echo "  # Build tool-only image"
    echo "  DOCKER_USERNAME=myuser \\"
    echo "    DEPLOY_MODELS=tool \\"
    echo "    TOOL_MODEL=yapwithai/yap-modernbert-screenshot-intent \\"
    echo "    ./build.sh"
    echo ""
    echo "  # Build both models"
    echo "  DOCKER_USERNAME=myuser \\"
    echo "    DEPLOY_MODELS=both \\"
    echo "    CHAT_MODEL=cpatonn/Qwen3-30B-A3B-Instruct-2507-AWQ-4bit \\"
    echo "    TOOL_MODEL=yapwithai/yap-modernbert-screenshot-intent \\"
    echo "    TAG=vllm-qwen3-full \\"
    echo "    ./build.sh"
    echo ""
    echo "Running the built image:"
    echo "  docker run -d --gpus all -e TEXT_API_KEY=xxx -p 8000:8000 myuser/yap-text-api:TAG"
    exit 0
}

# No command-line flags supported except --help
if [[ "${1:-}" == "--help" ]]; then
    usage
fi

# Validate configuration
if [[ "${DOCKER_USERNAME}" == "your-username" ]]; then
    log_error "Please set DOCKER_USERNAME environment variable"
    log_info "Example: DOCKER_USERNAME=myuser $0"
    exit 1
fi

# Validate models based on deploy mode
log_info "Validating models for DEPLOY_MODELS=${DEPLOY_MODELS_VAL}..."
if ! validate_models_for_deploy "${DEPLOY_MODELS_VAL}" "${CHAT_MODEL}" "${TOOL_MODEL}"; then
    log_error "Model validation failed. Build aborted."
    exit 1
fi

require_docker

ensure_docker_login

log_info "Building Yap Text Inference Docker image (vLLM)"
log_info "Image: ${FULL_IMAGE_NAME}"
log_info "Deploy mode: ${DEPLOY_MODELS_VAL}"
[[ -n "${CHAT_MODEL}" ]] && log_info "Chat model: ${CHAT_MODEL}"
[[ -n "${TOOL_MODEL}" ]] && log_info "Tool model: ${TOOL_MODEL}"
log_info "Platform: ${PLATFORM}"
log_info "Build context (stack): ${BUILD_CONTEXT}"
log_info "Dockerfile: ${DOCKERFILE}"

# Build the image
log_info "Preparing build context..."

prepare_build_context
log_info "Starting Docker build from temp context: ${BUILD_CONTEXT}"

init_build_args

# Add model build args - these become ENV vars in the image
BUILD_ARGS+=(--build-arg "DEPLOY_MODELS=${DEPLOY_MODELS_VAL}")
[[ -n "${CHAT_MODEL}" ]] && BUILD_ARGS+=(--build-arg "CHAT_MODEL=${CHAT_MODEL}")
[[ -n "${TOOL_MODEL}" ]] && BUILD_ARGS+=(--build-arg "TOOL_MODEL=${TOOL_MODEL}")

docker build "${BUILD_ARGS[@]}" "${BUILD_CONTEXT}"

log_success "Docker build completed successfully!"
log_info "Image: ${FULL_IMAGE_NAME}"

# Push the image
log_info "Pushing image to Docker Hub..."

# Try push; if unauthorized, attempt non-interactive login and retry once
if ! docker push "${FULL_IMAGE_NAME}"; then
    log_warn "Initial docker push failed. Attempting non-interactive login and retry..."
    ensure_docker_login || true
    if ! docker push "${FULL_IMAGE_NAME}"; then
        log_error "Docker push failed. Please run 'docker login' and ensure DOCKER_USERNAME has access to push ${FULL_IMAGE_NAME}."
        exit 1
    fi
fi

log_success "Image pushed successfully to Docker Hub!"
log_info "Pull command: docker pull ${FULL_IMAGE_NAME}"

# Provide usage examples
log_info ""
log_info "Usage:"
log_info ""
log_info "docker run -d --gpus all --name yap-server \\"
log_info "  -v yap-cache:/app/.hf \\"
log_info "  -e TEXT_API_KEY=your_secret_key \\"
log_info "  -p 8000:8000 \\"
log_info "  ${FULL_IMAGE_NAME}"
log_info ""
log_info "Health: curl http://localhost:8000/healthz"
log_success "Build process completed!"

