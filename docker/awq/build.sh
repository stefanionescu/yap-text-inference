#!/usr/bin/env bash
set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC2034  # sourced helper scripts rely on ROOT_DIR
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Docker configuration
DOCKER_USERNAME="${DOCKER_USERNAME:-your-username}"
# Enforce fixed image name
IMAGE_NAME="yap-text-inference-awq"

# Label/tag must reflect DEPLOY_MODELS
DEPLOY_MODELS_VAL="${DEPLOY_MODELS:-both}"
case "${DEPLOY_MODELS_VAL}" in
  chat|tool|both) ;;
  *)
    echo "[WARN] Invalid DEPLOY_MODELS='${DEPLOY_MODELS_VAL}', defaulting to 'both'" >&2
    DEPLOY_MODELS_VAL="both"
    ;;
esac

TAG="${DEPLOY_MODELS_VAL}"
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

# Usage function
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Build and push Yap Text Inference Docker image for AWQ deployment"
    echo ""
    echo "Environment Variables:"
    echo "  DOCKER_USERNAME     - Docker Hub username (required)"
    echo "  DEPLOY_MODELS       - chat|tool|both (controls image tag; default: both)"
    echo "  PLATFORM            - Target platform (default: linux/amd64)"
    echo ""
    echo "Options:"
    echo "  --help              - Show this help message"
    echo ""
    echo "Examples:"
    echo "  DOCKER_USERNAME=myuser DEPLOY_MODELS=both ./build.sh"
    echo "  DOCKER_USERNAME=myuser DEPLOY_MODELS=chat ./build.sh"
    echo "  DOCKER_USERNAME=myuser DEPLOY_MODELS=tool ./build.sh"
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

require_docker

ensure_docker_login

log_info "Building Yap Text Inference Docker image"
log_info "Image: ${FULL_IMAGE_NAME} (DEPLOY_MODELS=${DEPLOY_MODELS_VAL})"
log_info "Platform: ${PLATFORM}"
log_info "Build context (stack): ${BUILD_CONTEXT}"
log_info "Dockerfile: ${DOCKERFILE}"

# Build the image
log_info "Preparing build context..."

prepare_build_context
log_info "Starting Docker build from temp context: ${BUILD_CONTEXT}"

init_build_args

docker build "${BUILD_ARGS[@]}" "${BUILD_CONTEXT}"

log_success "Docker build completed successfully!"
log_info "Image size: $(docker images "${FULL_IMAGE_NAME}" --format "{{.Size}}")"
log_info "Image ID: $(docker images "${FULL_IMAGE_NAME}" --format "{{.ID}}")"

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
log_info "  -e CHAT_MODEL=your-org/chat-awq \\"
log_info "  -e TOOL_MODEL=your-org/tool-awq \\"
log_info "  -e TEXT_API_KEY=your_secret_key \\"
log_info "  -e CHAT_GPU_FRAC=0.70 \\"
log_info "  -e TOOL_GPU_FRAC=0.20 \\"
log_info "  -p 8000:8000 \\"
log_info "  ${FULL_IMAGE_NAME}"
log_info ""
log_info "Health: curl http://localhost:8000/healthz"
log_success "Build process completed!"
