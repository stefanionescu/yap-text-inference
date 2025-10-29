#!/usr/bin/env bash
set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Docker configuration
DOCKER_USERNAME="${DOCKER_USERNAME:-your-username}"
IMAGE_NAME="${IMAGE_NAME:-yap-text-inference-base}"
TAG="${TAG:-latest}"
FULL_IMAGE_NAME="${DOCKER_USERNAME}/${IMAGE_NAME}:${TAG}"

# Build configuration
PLATFORM="${PLATFORM:-linux/amd64}"
DOCKERFILE="${SCRIPT_DIR}/Dockerfile"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error(){ echo -e "${RED}[ERROR]${NC} $1"; }
log_success(){ echo -e "${GREEN}[SUCCESS]${NC} $1"; }

usage() {
  echo "Usage: $0"
  echo ""
  echo "Build and push Yap Text Inference Docker image (Base stack)"
  echo ""
  echo "Environment Variables:"
  echo "  DOCKER_USERNAME      - Docker Hub username (default: your-username)"
  echo "  IMAGE_NAME           - Docker image name (default: yap-text-inference-base)"
  echo "  TAG                  - Docker image tag (default: latest)"
  echo "  PLATFORM             - Target platform (default: linux/amd64)"
  echo ""
  echo "Optional Build-Time Preload Args (passed via --build-arg if set):"
  echo "  PRELOAD_MODELS=0|1   - Preload repos into image (default 0)"
  echo "  DEPLOY_MODELS=both|chat|tool"
  echo "  CHAT_MODEL           - Float/GPTQ chat repo (one source per engine)"
  echo "  TOOL_MODEL           - Float/GPTQ tool repo (one source per engine)"
  echo "  AWQ_CHAT_MODEL       - Pre-quantized AWQ chat repo (mutually exclusive with CHAT_MODEL)"
  echo "  AWQ_TOOL_MODEL       - Pre-quantized AWQ tool repo (mutually exclusive with TOOL_MODEL)"
  echo "  HF_TOKEN             - HF token for gated/private repos"
  echo ""
  echo "Examples:"
  echo "  DOCKER_USERNAME=myuser ${0}"
  echo "  TAG=v1.0.0 DOCKER_USERNAME=myuser ${0}"
  echo "  PRELOAD_MODELS=1 DEPLOY_MODELS=both CHAT_MODEL=org/chat TOOL_MODEL=org/tool DOCKER_USERNAME=myuser ${0}"
  exit 0
}

if [[ "${1:-}" == "--help" ]]; then
  usage
fi

if [[ "${DOCKER_USERNAME}" == "your-username" ]]; then
  log_error "Please set DOCKER_USERNAME environment variable"
  log_info "Example: DOCKER_USERNAME=myuser $0"
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  log_error "Docker is not running. Please start Docker and try again."
  exit 1
fi

ensure_docker_login() {
  if docker info 2>/dev/null | grep -q "Username:"; then
    log_info "Docker login detected."
    return
  fi
  if [ -n "${DOCKER_PASSWORD:-}" ]; then
    echo "${DOCKER_PASSWORD}" | docker login -u "${DOCKER_USERNAME}" --password-stdin && return
  fi
  if [ -n "${DOCKER_TOKEN:-}" ]; then
    echo "${DOCKER_TOKEN}" | docker login -u "${DOCKER_USERNAME}" --password-stdin && return
  fi
  log_warn "Not logged in to Docker Hub and no DOCKER_PASSWORD/DOCKER_TOKEN set; push may fail."
}
ensure_docker_login

log_info "Building Yap Text Inference Docker image (Base)"
log_info "Image: ${FULL_IMAGE_NAME}"
log_info "Platform: ${PLATFORM}"
log_info "Dockerfile: ${DOCKERFILE}"

# Prepare temp build context (ensures only necessary files are sent)
TMP_BUILD_DIR="$(mktemp -d -t yap-base-build-XXXXXX)"
cleanup() { rm -rf "${TMP_BUILD_DIR}" 2>/dev/null || true; }
trap cleanup EXIT

cp -a "${DOCKERFILE}" "${TMP_BUILD_DIR}/Dockerfile"
cp -a "${SCRIPT_DIR}/scripts" "${TMP_BUILD_DIR}/scripts"
cp -a "${ROOT_DIR}/requirements.txt" "${TMP_BUILD_DIR}/requirements.txt"
cp -a "${ROOT_DIR}/src" "${TMP_BUILD_DIR}/src"
cp -a "${ROOT_DIR}/prompts" "${TMP_BUILD_DIR}/prompts"
cp -a "${ROOT_DIR}/test" "${TMP_BUILD_DIR}/test"

BUILD_ARGS=(
  --file "${TMP_BUILD_DIR}/Dockerfile"
  --tag "${FULL_IMAGE_NAME}"
  --platform "${PLATFORM}"
)

# Append optional build args if provided
append_arg() { local k="$1"; local v="$2"; if [ -n "${v}" ]; then BUILD_ARGS+=(--build-arg "${k}=${v}"); fi; }
append_arg PRELOAD_MODELS "${PRELOAD_MODELS:-}"
append_arg DEPLOY_MODELS "${DEPLOY_MODELS:-}"
append_arg CHAT_MODEL "${CHAT_MODEL:-}"
append_arg TOOL_MODEL "${TOOL_MODEL:-}"
append_arg AWQ_CHAT_MODEL "${AWQ_CHAT_MODEL:-}"
append_arg AWQ_TOOL_MODEL "${AWQ_TOOL_MODEL:-}"
append_arg HF_TOKEN "${HF_TOKEN:-}"

log_info "Starting Docker build from temp context: ${TMP_BUILD_DIR}"
docker build "${BUILD_ARGS[@]}" "${TMP_BUILD_DIR}"

log_success "Docker build completed successfully!"
log_info "Image size: $(docker images "${FULL_IMAGE_NAME}" --format "{{.Size}}")"
log_info "Image ID: $(docker images "${FULL_IMAGE_NAME}" --format "{{.ID}}")"

log_info "Pushing image to Docker Hub..."
if ! docker push "${FULL_IMAGE_NAME}"; then
  log_warn "Initial docker push failed. Attempting non-interactive login and retry..."
  ensure_docker_login || true
  if ! docker push "${FULL_IMAGE_NAME}"; then
    log_error "Docker push failed. Please run 'docker login' and ensure DOCKER_USERNAME can push ${FULL_IMAGE_NAME}."
    exit 1
  fi
fi

log_success "Image pushed successfully to Docker Hub!"
log_info "Pull command: docker pull ${FULL_IMAGE_NAME}"
log_info ""
log_info "Usage:"
log_info "docker run -d --gpus all --name yap-base \\\" 
log_info "  -e CHAT_MODEL=your-org/float-or-gptq-chat \\\" 
log_info "  -e TOOL_MODEL=your-org/float-or-gptq-tool \\\" 
log_info "  -e YAP_TEXT_API_KEY=yap_token \\\" 
log_info "  -p 8000:8000 \\\" 
log_info "  ${FULL_IMAGE_NAME}"
log_info ""
log_info "Health: curl http://localhost:8000/healthz"
log_success "Build process completed!"


