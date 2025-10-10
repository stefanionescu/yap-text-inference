#!/usr/bin/env bash
set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Docker configuration
DOCKER_USERNAME="${DOCKER_USERNAME:-your-username}"
IMAGE_NAME="${IMAGE_NAME:-yap-text-inference-auto-quant}"
TAG="${TAG:-latest}"
FULL_IMAGE_NAME="${DOCKER_USERNAME}/${IMAGE_NAME}:${TAG}"

# Build configuration
PLATFORM="${PLATFORM:-linux/amd64}"
# Use stack directory as primary build context so its local .dockerignore applies
BUILD_CONTEXT="${SCRIPT_DIR}"
DOCKERFILE="${SCRIPT_DIR}/Dockerfile"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Build and push Yap Text Inference Docker image for FP8/GPTQ auto-quant deployment"
    echo ""
    echo "Environment Variables:"
    echo "  DOCKER_USERNAME     - Docker Hub username (default: your-username)"
    echo "  IMAGE_NAME          - Docker image name (default: yap-text-inference-auto-quant)"
    echo "  TAG                 - Docker image tag (default: latest)"
    echo "  PLATFORM            - Target platform (default: linux/amd64)"
    echo ""
    echo "Options:"
    echo "  --help              - Show this help message"
    echo ""
    echo "Examples:"
    echo "  DOCKER_USERNAME=myuser ./build.sh"
    echo "  TAG=v1.0.0 ./build.sh"
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

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    log_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

:

log_info "Building Yap Text Inference Docker image (FP8/GPTQ)"
log_info "Image: ${FULL_IMAGE_NAME}"
log_info "Platform: ${PLATFORM}"
log_info "Build context: ${BUILD_CONTEXT}"
log_info "Dockerfile: ${DOCKERFILE}"

# Build the image
log_info "Starting Docker build..."

BUILD_ARGS=(
    --file "${DOCKERFILE}"
    --tag "${FULL_IMAGE_NAME}"
    --platform "${PLATFORM}"
)

docker build "${BUILD_ARGS[@]}" "${BUILD_CONTEXT}"

log_success "Docker build completed successfully!"
log_info "Image size: $(docker images "${FULL_IMAGE_NAME}" --format "{{.Size}}")"
log_info "Image ID: $(docker images "${FULL_IMAGE_NAME}" --format "{{.ID}}")"

# Push the image
log_info "Pushing image to Docker Hub..."

# Check if logged in to Docker Hub
if ! docker info | grep -q "Username:"; then
    log_error "Not logged in to Docker Hub. Please run 'docker login' then re-run this script."
    exit 1
fi

docker push "${FULL_IMAGE_NAME}"

log_success "Image pushed successfully to Docker Hub!"
log_info "Pull command: docker pull ${FULL_IMAGE_NAME}"

# Usage examples
log_info ""
log_info "Usage:"
log_info ""
log_info "docker run -d --gpus all --name yap-server \\
  -e CHAT_MODEL=your-org/chat-model \\
  -e TOOL_MODEL=your-org/tool-model \\
  -e YAP_TEXT_API_KEY=yap_token \\
  -e WARMUP_ON_START=0 \\
  -e CHAT_GPU_FRAC=0.70 \\
  -e TOOL_GPU_FRAC=0.20 \\
  -p 8000:8000 \\
  ${FULL_IMAGE_NAME}"
log_info ""
log_info "Health: curl http://localhost:8000/healthz"
log_success "Build process completed!"


