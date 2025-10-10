#!/usr/bin/env bash
set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Docker configuration
DOCKER_USERNAME="${DOCKER_USERNAME:-your-username}"
IMAGE_NAME="${IMAGE_NAME:-yap-text-inference-awq}"
TAG="${TAG:-latest}"
FULL_IMAGE_NAME="${DOCKER_USERNAME}/${IMAGE_NAME}:${TAG}"

# Build configuration
PLATFORM="${PLATFORM:-linux/amd64}"
BUILD_CONTEXT="${ROOT_DIR}"
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

# Usage function
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Build and push Yap Text Inference Docker image for AWQ deployment"
    echo ""
    echo "Environment Variables:"
    echo "  DOCKER_USERNAME     - Docker Hub username (default: your-username)"
    echo "  IMAGE_NAME          - Docker image name (default: yap-text-inference-awq)"
    echo "  TAG                 - Docker image tag (default: latest)"
    echo "  PLATFORM            - Target platform (default: linux/amd64)"
    echo ""
    echo "Options:"
    echo "  --build-only        - Only build, don't push to Docker Hub"
    echo "  --push-only         - Only push existing image (skip build)"
    echo "  --multi-platform    - Build for multiple platforms (amd64,arm64)"
    echo "  --no-cache          - Build without using Docker cache"
    echo "  --help              - Show this help message"
    echo ""
    echo "Examples:"
    echo "  # Basic build and push"
    echo "  DOCKER_USERNAME=myuser ./build.sh"
    echo ""
    echo "  # Build only (no push)"
    echo "  ./build.sh --build-only"
    echo ""
    echo "  # Multi-platform build"
    echo "  ./build.sh --multi-platform"
    echo ""
    echo "  # Build with custom tag"
    echo "  TAG=v1.0.0 ./build.sh"
    exit 0
}

# Parse command line arguments
BUILD_ONLY=false
PUSH_ONLY=false
MULTI_PLATFORM=false
NO_CACHE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --build-only)
            BUILD_ONLY=true
            shift
            ;;
        --push-only)
            PUSH_ONLY=true
            shift
            ;;
        --multi-platform)
            MULTI_PLATFORM=true
            PLATFORM="linux/amd64,linux/arm64"
            shift
            ;;
        --no-cache)
            NO_CACHE=true
            shift
            ;;
        --help)
            usage
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            ;;
    esac
done

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

# Check if buildx is available for multi-platform builds
if [[ "${MULTI_PLATFORM}" == "true" ]]; then
    if ! docker buildx version >/dev/null 2>&1; then
        log_error "Docker buildx is required for multi-platform builds"
        exit 1
    fi
fi

log_info "Building Yap Text Inference Docker image"
log_info "Image: ${FULL_IMAGE_NAME}"
log_info "Platform: ${PLATFORM}"
log_info "Build context: ${BUILD_CONTEXT}"
log_info "Dockerfile: ${DOCKERFILE}"

# Build the image
if [[ "${PUSH_ONLY}" == "false" ]]; then
    log_info "Starting Docker build..."
    
    BUILD_ARGS=(
        --file "${DOCKERFILE}"
        --tag "${FULL_IMAGE_NAME}"
        --platform "${PLATFORM}"
    )
    
    if [[ "${NO_CACHE}" == "true" ]]; then
        BUILD_ARGS+=(--no-cache)
    fi
    
    if [[ "${MULTI_PLATFORM}" == "true" ]]; then
        # Use buildx for multi-platform
        docker buildx build "${BUILD_ARGS[@]}" "${BUILD_CONTEXT}"
    else
        # Use regular build
        docker build "${BUILD_ARGS[@]}" "${BUILD_CONTEXT}"
    fi
    
    log_success "Docker build completed successfully!"
    
    # Show image info
    if [[ "${MULTI_PLATFORM}" == "false" ]]; then
        log_info "Image size: $(docker images "${FULL_IMAGE_NAME}" --format "{{.Size}}")"
        log_info "Image ID: $(docker images "${FULL_IMAGE_NAME}" --format "{{.ID}}")"
    fi
fi

# Push the image
if [[ "${BUILD_ONLY}" == "false" ]]; then
    log_info "Pushing image to Docker Hub..."
    
    # Check if logged in to Docker Hub
    if ! docker info | grep -q "Username:"; then
        log_warn "Not logged in to Docker Hub. Please run 'docker login' first."
        read -p "Do you want to login now? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker login
        else
            log_error "Docker login required to push image"
            exit 1
        fi
    fi
    
    if [[ "${MULTI_PLATFORM}" == "true" ]]; then
        # Push multi-platform image using buildx
        docker buildx build "${BUILD_ARGS[@]}" --push "${BUILD_CONTEXT}"
    else
        # Push regular image
        docker push "${FULL_IMAGE_NAME}"
    fi
    
    log_success "Image pushed successfully to Docker Hub!"
    log_info "Pull command: docker pull ${FULL_IMAGE_NAME}"
fi

# Provide usage examples
log_info ""
log_info "Usage:"
log_info ""
log_info "docker run -d --gpus all --name yap-server \\"
log_info "  -e AWQ_CHAT_MODEL=your-org/chat-awq \\"
log_info "  -e AWQ_TOOL_MODEL=your-org/tool-awq \\"
log_info "  -e YAP_API_KEY=yap_token \\"
log_info "  -e WARMUP_ON_START=0 \\"
log_info "  -e CHAT_GPU_FRAC=0.70 \\"
log_info "  -e TOOL_GPU_FRAC=0.20 \\"
log_info "  -p 8000:8000 \\"
log_info "  ${FULL_IMAGE_NAME}"
log_info ""
log_info "Health: curl http://localhost:8000/healthz"
log_success "Build process completed!"
