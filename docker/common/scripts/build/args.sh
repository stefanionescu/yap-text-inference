#!/usr/bin/env bash
# Shared build argument initialization for Docker builds.
#
# Initializes the BUILD_ARGS array with common Docker build flags. The parent
# build script must define DOCKERFILE and FULL_IMAGE_NAME before sourcing this
# file. Repo Docker builds are always linux/amd64.

# shellcheck disable=SC2034  # consumed by parent build script after sourcing
init_build_args() {
  BUILD_ARGS=(
    --file "${DOCKERFILE}"
    --tag "${FULL_IMAGE_NAME}"
    --platform "linux/amd64"
  )
  if [ "${NO_CACHE:-0}" = "1" ]; then
    BUILD_ARGS+=(--no-cache)
  fi
}
