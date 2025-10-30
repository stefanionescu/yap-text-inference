#!/usr/bin/env bash

init_build_args() {
  BUILD_ARGS=(
    --file "${TMP_BUILD_DIR}/Dockerfile"
    --tag "${FULL_IMAGE_NAME}"
    --platform "${PLATFORM}"
  )
}

append_arg() {
  local k="$1"; local v="$2"
  if [ -n "${v}" ]; then BUILD_ARGS+=(--build-arg "${k}=${v}"); fi
}


