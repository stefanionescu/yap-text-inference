#!/usr/bin/env bash
# Build context preparation for TRT Docker images.
#
# Creates a temporary directory with all files needed for the Docker build,
# including shared utilities from common/ and TRT-specific download scripts.

prepare_build_context() {
  TMP_BUILD_DIR="$(mktemp -d -t yap-trt-build-XXXXXX)"
  trap 'rm -rf "${TMP_BUILD_DIR}" 2>/dev/null || true' EXIT

  cp -a "${DOCKERFILE}" "${TMP_BUILD_DIR}/Dockerfile"
  cp -a "${SCRIPT_DIR}/scripts" "${TMP_BUILD_DIR}/scripts"
  cp -a "${ROOT_DIR}/requirements-trt.txt" "${TMP_BUILD_DIR}/requirements.txt"
  cp -a "${ROOT_DIR}/src" "${TMP_BUILD_DIR}/src"

  # Copy download scripts - TRT-specific ones first, then shared tool download
  cp -a "${SCRIPT_DIR}/download" "${TMP_BUILD_DIR}/download"
  cp -a "${SCRIPT_DIR}/../common/download/download_tool.py" "${TMP_BUILD_DIR}/download/download_tool.py"

  # shellcheck disable=SC2034  # consumed by parent build script after sourcing
  BUILD_CONTEXT="${TMP_BUILD_DIR}"
}

