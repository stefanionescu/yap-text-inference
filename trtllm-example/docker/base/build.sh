#!/usr/bin/env bash
set -euo pipefail

# Build the base image that replicates bootstrap + TRT install

IMAGE_NAME=${IMAGE_NAME:-sionescu/orpheus-trtllm-base}
IMAGE_TAG=${IMAGE_TAG:-cu130-py310}
PUSH_IMAGE=${PUSH_IMAGE:-1}

usage() {
  cat <<'EOF'
Usage: docker/base/build.sh

Builds the Orpheus TRT-LLM base image and pushes to the configured registry
(default docker.io) by default. To skip pushing, set PUSH_IMAGE=0.
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

# Optional: pass HF_TOKEN at build time if you want to bake auth (not recommended)
# Resolve MODEL_ID from MODEL_PRESET when not explicitly provided
MODEL_PRESET=${MODEL_PRESET:-canopy}
MODEL_ID_EFFECTIVE=${MODEL_ID:-}
if [[ -z ${MODEL_ID_EFFECTIVE} ]]; then
  if [[ ${MODEL_PRESET} == "fast" ]]; then
    MODEL_ID_EFFECTIVE="yapwithai/fast-orpheus-3b-0.1-ft"
  else
    MODEL_ID_EFFECTIVE="yapwithai/canopy-orpheus-3b-0.1-ft"
  fi
fi
BUILD_ARGS=(
  --build-arg "PYTORCH_INDEX_URL=${PYTORCH_INDEX_URL:-https://download.pytorch.org/whl/cu130}"
  --build-arg "TRTLLM_PIP_SPEC=${TRTLLM_PIP_SPEC:-tensorrt_llm==1.2.0rc5}"
  --build-arg "TRTLLM_WHEEL_URL=${TRTLLM_WHEEL_URL:-}"
  ${HF_TOKEN:+--build-arg HF_TOKEN=$HF_TOKEN}
  --build-arg "MODEL_ID=${MODEL_ID_EFFECTIVE}"
  --build-arg "TRTLLM_REPO_URL=${TRTLLM_REPO_URL:-https://github.com/Yap-With-AI/TensorRT-LLM.git}"
)

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)

cd "$REPO_ROOT"

echo "Building ${IMAGE_NAME}:${IMAGE_TAG} (platform linux/amd64)"
docker build \
  --platform linux/amd64 \
  -f docker/base/Dockerfile \
  -t "${IMAGE_NAME}:${IMAGE_TAG}" \
  ${HF_TOKEN:+--secret id=HF_TOKEN,env=HF_TOKEN} \
  "${BUILD_ARGS[@]}" \
  .

printf "\nBuilt image: %s:%s\n" "$IMAGE_NAME" "$IMAGE_TAG"
echo "Use this as a base in cloud to skip bootstrap and TRT installs."

if [[ $PUSH_IMAGE == "1" ]]; then
  printf "\nPushing %s:%s...\n" "$IMAGE_NAME" "$IMAGE_TAG"
  docker push "${IMAGE_NAME}:${IMAGE_TAG}"
  echo "Pushed ${IMAGE_NAME}:${IMAGE_TAG}"
else
  printf "\nTo push: docker push %s:%s\n" "$IMAGE_NAME" "$IMAGE_TAG"
  echo "(Or rerun with --push / PUSH_IMAGE=1)"
fi
