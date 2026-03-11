#!/usr/bin/env bash
# shellcheck disable=SC1091
set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC2034  # sourced helper scripts rely on ROOT_DIR
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
COMMON_DIR="${SCRIPT_DIR}/../common"
source "${COMMON_DIR}/scripts/build/defaults.sh"
build_init_tool_defaults

# Force tool-only deploy mode
DEPLOY_MODE_VAL="tool"

# Validate tag naming convention for tool-only images
if [[ ! ${TAG} =~ ^tool- ]]; then
  echo "[build] ✗ TAG must start with 'tool-' for tool-only images" >&2
  echo "[build]   Got: ${TAG}" >&2
  echo "[build]   Example: tool-modernbert" >&2
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
if [[ ${1-} == "--help" ]]; then
  usage
fi

validate_tag_prefix "${TAG}" "tool-" "tool-only" "tool-modernbert"

# validate_stack_build - Run shared model validation for the tool-only stack.
validate_stack_build() {
  log_info "[build] Validating models for DEPLOY_MODE=tool..."
  if ! validate_models_for_deploy_common "" "tool" "" "${TOOL_MODEL}"; then
    log_err "[build] ✗ Model validation failed. Build aborted."
    exit 1
  fi
}

# log_stack_build - Print the tool-only build summary before docker build.
log_stack_build() {
  log_info "[build] Tool-only image (no chat engine)"
  log_info "[build]   Tool model: ${TOOL_MODEL}"
}

# append_stack_build_args - Add tool-only build arguments to BUILD_ARGS.
append_stack_build_args() {
  BUILD_ARGS+=(--build-arg "DEPLOY_MODE=${DEPLOY_MODE_VAL}")
  [[ -n ${TOOL_MODEL} ]] && BUILD_ARGS+=(--build-arg "TOOL_MODEL=${TOOL_MODEL}")
  [[ -n ${HF_TOKEN} ]] && BUILD_ARGS+=(--secret "id=hf_token,env=HF_TOKEN")
}

run_stack_build "${SCRIPT_DIR}" "requirements-tool.txt" "0" "yap-tool"
