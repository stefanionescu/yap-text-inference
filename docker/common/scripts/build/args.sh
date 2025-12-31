#!/usr/bin/env bash
# Shared build argument initialization for Docker builds.
#
# Initializes the BUILD_ARGS array with common Docker build flags. The parent
# build script must define DOCKERFILE, FULL_IMAGE_NAME, and PLATFORM before
# sourcing this file.

# shellcheck disable=SC2034  # consumed by parent build script after sourcing
init_build_args() {
  BUILD_ARGS=(
    --file "${DOCKERFILE}"
    --tag "${FULL_IMAGE_NAME}"
    --platform "${PLATFORM}"
  )
}

