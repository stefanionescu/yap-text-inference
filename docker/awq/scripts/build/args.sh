#!/usr/bin/env bash

# shellcheck disable=SC2034  # consumed by parent build script after sourcing
init_build_args() {
  BUILD_ARGS=(
    --file "${DOCKERFILE}"
    --tag "${FULL_IMAGE_NAME}"
    --platform "${PLATFORM}"
  )
}


