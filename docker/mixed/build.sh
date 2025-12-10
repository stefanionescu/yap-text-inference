#!/usr/bin/env bash
set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC2034  # sourced helper scripts rely on ROOT_DIR
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Docker configuration
DOCKER_USERNAME="${DOCKER_USERNAME:-your-username}"
# Enforce fixed image name for mixed stack
IMAGE_NAME="yap-text-inference-mixed"

source "${ROOT_DIR}/scripts/lib/common/model_detect.sh"

# Determine tag from DEPLOY_MODELS and provided model types (AWQ vs float)
DEPLOY_MODELS_VAL="${DEPLOY_MODELS:-both}"
case "${DEPLOY_MODELS_VAL}" in
  chat|tool|both) ;;
  *) echo "[WARN] Invalid DEPLOY_MODELS='${DEPLOY_MODELS_VAL}', defaulting to 'both'" >&2; DEPLOY_MODELS_VAL="both" ;;
esac

# Normalize presence of build-time sources
CHAT_IS_AWQ=0; TOOL_IS_AWQ=0
if [ "${DEPLOY_MODELS_VAL}" != "tool" ]; then
  if [ -z "${CHAT_MODEL:-}" ]; then
    echo "[ERROR] CHAT_MODEL must be provided when deploying chat/both" >&2; exit 1
  fi
  if model_detect_is_awq_name "${CHAT_MODEL}"; then
    CHAT_IS_AWQ=1
  fi
fi
if [ "${DEPLOY_MODELS_VAL}" != "chat" ]; then
  if [ -z "${TOOL_MODEL:-}" ]; then
    echo "[ERROR] TOOL_MODEL must be provided when deploying tool/both" >&2; exit 1
  fi
  if model_detect_is_awq_name "${TOOL_MODEL}"; then
    TOOL_IS_AWQ=1
  fi
fi

case "${DEPLOY_MODELS_VAL}" in
  chat)
    if [ ${CHAT_IS_AWQ} -eq 1 ]; then TAG="chat-awq"; else TAG="chat-fp8"; fi ;;
  tool)
    if [ ${TOOL_IS_AWQ} -eq 1 ]; then TAG="tool-awq"; else TAG="tool-fp8"; fi ;;
  both)
    if [ ${CHAT_IS_AWQ} -eq 1 ] && [ ${TOOL_IS_AWQ} -eq 1 ]; then
      TAG="both-awq"
    elif [ ${CHAT_IS_AWQ} -eq 0 ] && [ ${TOOL_IS_AWQ} -eq 0 ]; then
      TAG="both-fp8"
    elif [ ${CHAT_IS_AWQ} -eq 0 ] && [ ${TOOL_IS_AWQ} -eq 1 ]; then
      TAG="both-chat-fp8-tool-awq"
    else
      TAG="both-chat-awq-tool-fp8"
    fi ;;
esac

FULL_IMAGE_NAME="${DOCKER_USERNAME}/${IMAGE_NAME}:${TAG}"

# Build configuration
PLATFORM="${PLATFORM:-linux/amd64}"
DOCKERFILE="${SCRIPT_DIR}/Dockerfile"

# Modules
source "${SCRIPT_DIR}/scripts/build/logs.sh"
source "${SCRIPT_DIR}/scripts/build/docker.sh"
source "${SCRIPT_DIR}/scripts/build/args.sh"
source "${SCRIPT_DIR}/scripts/build/context.sh"

usage() {
  echo "Usage: $0"
  echo ""
  echo "Build and push Yap Text Inference Docker image (Mixed stack)"
  echo ""
  echo "Environment Variables:"
  echo "  DOCKER_USERNAME      - Docker Hub username (required)"
  echo "  DEPLOY_MODELS        - chat|tool|both (default: both)"
  echo "  CHAT_MODEL           - Chat repo/path (float, GPTQ, AWQ, W4A16 supported)"
  echo "  TOOL_MODEL           - Tool repo/path (float, GPTQ, AWQ, W4A16 supported)"
  echo "  PLATFORM             - Target platform (default: linux/amd64)"
  echo ""
  echo "Build-Time Args (passed via --build-arg):"
  echo "  DEPLOY_MODELS=both|chat|tool"
  echo "  CHAT_MODEL           - Chat repo/path (one source per engine)"
  echo "  TOOL_MODEL           - Tool repo/path (one source per engine)"
  echo "  HF_TOKEN             - HF token for gated/private repos"
  echo ""
  echo "Examples:"
  echo "  DOCKER_USERNAME=myuser DEPLOY_MODELS=both CHAT_MODEL=org/chat TOOL_MODEL=org/tool ${0}   # -> :both-fp8"
  echo "  DOCKER_USERNAME=myuser DEPLOY_MODELS=both CHAT_MODEL=org/chat-awq TOOL_MODEL=org/tool-awq ${0}   # -> :both-awq"
  echo "  DOCKER_USERNAME=myuser DEPLOY_MODELS=chat CHAT_MODEL=org/chat-awq ${0}   # -> :chat-awq"
  echo "  DOCKER_USERNAME=myuser DEPLOY_MODELS=tool TOOL_MODEL=org/tool ${0}   # -> :tool-fp8"
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

require_docker

ensure_docker_login

log_info "Building Yap Text Inference Docker image (Mixed)"
log_info "Image: ${FULL_IMAGE_NAME}"
log_info "Platform: ${PLATFORM}"
log_info "Dockerfile: ${DOCKERFILE}"

prepare_build_context

init_build_args

# Append optional build args if provided
append_arg DEPLOY_MODELS "${DEPLOY_MODELS:-}"
append_arg CHAT_MODEL "${CHAT_MODEL:-}"
append_arg TOOL_MODEL "${TOOL_MODEL:-}"
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
log_info "docker run -d --gpus all --name yap-base \\"
log_info "  -e TEXT_API_KEY=your_secret_key \\"
log_info "  -p 8000:8000 \\"
log_info "  ${FULL_IMAGE_NAME}"
log_info ""
log_info "Health: curl http://localhost:8000/healthz"
log_success "Build process completed!"
