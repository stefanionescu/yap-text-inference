#!/usr/bin/env bash

init_build_args() {
  BUILD_ARGS=(
    --file "${DOCKERFILE}"
    --tag "${FULL_IMAGE_NAME}"
    --platform "${PLATFORM}"
  )
}


