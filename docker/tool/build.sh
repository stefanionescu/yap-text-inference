#!/usr/bin/env bash
# shellcheck disable=SC1091
set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC2034  # sourced helper scripts rely on ROOT_DIR
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Docker configuration
DOCKER_USERNAME="${DOCKER_USERNAME:-your-username}"
IMAGE_NAME="${IMAGE_NAME:-yap-text-api}"

# Force tool-only deploy mode
DEPLOY_MODE_VAL="tool"

# Model configuration
TOOL_MODEL="${TOOL_MODEL:-}"

# HuggingFace token for private repos
HF_TOKEN="${HF_TOKEN:-}"

# Custom tag
TAG="${TAG:-tool-only}"

# Validate tag naming convention for tool-only images
if [[ ! ${TAG} =~ ^tool- ]]; then
  echo "[build] ✗ TAG must start with 'tool-' for tool-only images" >&2
  echo "[build]   Got: ${TAG}" >&2
  echo "[build]   Example: tool-modernbert" >&2
  exit 1
fi

FULL_IMAGE_NAME="${DOCKER_USERNAME}/${IMAGE_NAME}:${TAG}"

# Build configuration
PLATFORM="${PLATFORM:-linux/amd64}"
# Use stack directory as primary build context so its local .dockerignore applies
BUILD_CONTEXT="${SCRIPT_DIR}"
# shellcheck disable=SC2034  # Used by sourced scripts
DOCKERFILE="${SCRIPT_DIR}/Dockerfile"

# Modules - shared utilities from common, tool-specific from local
COMMON_DIR="${SCRIPT_DIR}/../common"
source "${COMMON_DIR}/scripts/logs.sh"
source "${COMMON_DIR}/scripts/build/docker.sh"
source "${COMMON_DIR}/scripts/build/args.sh"
source "${COMMON_DIR}/scripts/build/context.sh"
source "${COMMON_DIR}/scripts/build/validate.sh"

# Usage function
usage() {
  echo "Usage: $0 [OPTIONS]"
  echo ""
  echo "Build and push Yap Text Inference Docker image (tool-only)"
  echo ""
  echo "IMPORTANT: The tool model is BAKED INTO the image at build time."
  echo "           No chat engine is included -- lightweight ~3-5GB image."
  echo ""
  echo "Environment Variables:"
  echo "  DOCKER_USERNAME     - Docker Hub username (required)"
  echo "  IMAGE_NAME          - Docker image name (default: yap-text-api)"
  echo "  TOOL_MODEL          - Tool model HF repo (required)"
  echo "  TAG                 - Image tag (MUST start with 'tool-'; default: tool-only)"
  echo "  PLATFORM            - Target platform (default: linux/amd64)"
  echo "  HF_TOKEN            - HuggingFace token (for private repos)"
  echo "  NO_CACHE            - Build without Docker cache (default: 0)"
  echo ""
  echo "Options:"
  echo "  --help              - Show this help message"
  echo ""
  echo "Examples:"
  cat <<'EOF'
  # Build tool-only image
  DOCKER_USERNAME=myuser \
    TOOL_MODEL=yapwithai/yap-modernbert-screenshot-intent \
    TAG=tool-test \
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
  log_err "[build] ✗ Please set DOCKER_USERNAME environment variable"
  log_info "[build] Example: DOCKER_USERNAME=myuser $0"
  exit 1
fi

# Validate tool model
log_info "[build] Validating models for DEPLOY_MODE=tool..."
if ! validate_models_for_deploy_common "" "tool" "" "${TOOL_MODEL}"; then
  log_err "[build] ✗ Model validation failed. Build aborted."
  exit 1
fi
echo # blank line after validation

require_docker

ensure_docker_login

log_info "[build] Building Docker image: ${FULL_IMAGE_NAME}..."
log_info "[build] Tool-only image (no chat engine)"
log_info "[build]   Tool model: ${TOOL_MODEL}"

# Build the image
prepare_build_context_common "${SCRIPT_DIR}" "requirements-tool.txt" "0" "yap-tool"

init_build_args

# Add model build args - only DEPLOY_MODE and TOOL_MODEL needed
BUILD_ARGS+=(--build-arg "DEPLOY_MODE=${DEPLOY_MODE_VAL}")
[[ -n ${TOOL_MODEL} ]] && BUILD_ARGS+=(--build-arg "TOOL_MODEL=${TOOL_MODEL}")
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
    log_err "[build] ✗ Docker push failed. Please run 'docker login' and ensure DOCKER_USERNAME has access to push ${FULL_IMAGE_NAME}."
    exit 1
  fi
fi

log_success "[build] ✓ Pushed ${FULL_IMAGE_NAME}"
