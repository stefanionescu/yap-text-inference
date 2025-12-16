#!/usr/bin/env bash
set -euo pipefail

# Build the fast production image with dependencies only

IMAGE_NAME=${IMAGE_NAME:-yap-orpheus-trt-tts-api}
IMAGE_TAG=${IMAGE_TAG:-latest}
PUSH_IMAGE=${PUSH_IMAGE:-1}

usage() {
  cat <<'EOF'
Usage: docker/awq/build.sh

Builds the Orpheus TTS fast production image with dependencies only, and pushes
to the configured registry (default docker.io) by default. To skip pushing, set
PUSH_IMAGE=0.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --push)
      PUSH_IMAGE=1
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

# Build arguments for customization (cu130 for TRT-LLM 1.2.0rc4's torch 2.9.x requirement)
BUILD_ARGS=(
  --build-arg "PYTORCH_INDEX_URL=${PYTORCH_INDEX_URL:-https://download.pytorch.org/whl/cu130}"
  --build-arg "TRTLLM_PIP_SPEC=${TRTLLM_PIP_SPEC:-tensorrt_llm==1.2.0rc4}"
  --build-arg "TRTLLM_WHEEL_URL=${TRTLLM_WHEEL_URL:-}"
)

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)

cd "$REPO_ROOT"

echo "Building ${IMAGE_NAME}:${IMAGE_TAG} (platform linux/amd64)"
echo "This is a lean production image with dependencies only ~16GB"

docker build \
  --platform linux/amd64 \
  -f docker/awq/Dockerfile \
  -t "${IMAGE_NAME}:${IMAGE_TAG}" \
  "${BUILD_ARGS[@]}" \
  .
# spacer to avoid hidden char issues on some shells
echo ""
echo "Built image: ${IMAGE_NAME}:${IMAGE_TAG}"
echo "Image size: ~16GB (lean production build)"
echo "Ready for production deployment with runtime model/engine mounting"

if [[ $PUSH_IMAGE == "1" ]]; then
  echo ""
  echo "Pushing ${IMAGE_NAME}:${IMAGE_TAG}..."
  docker push "${IMAGE_NAME}:${IMAGE_TAG}"
  echo "Pushed ${IMAGE_NAME}:${IMAGE_TAG}"
else
  echo ""
  echo "To push: docker push ${IMAGE_NAME}:${IMAGE_TAG}"
  echo "(Or rerun with --push / PUSH_IMAGE=1)"
fi
