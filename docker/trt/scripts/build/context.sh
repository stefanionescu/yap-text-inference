#!/usr/bin/env bash
# Build context preparation for TRT Docker images.
#
# Creates a temporary directory with all files needed for the Docker build,
# including shared utilities from common/ and TRT-specific download scripts.

prepare_build_context() {
  TMP_BUILD_DIR="$(mktemp -d -t yap-trt-build-XXXXXX)"
  trap 'rm -rf "${TMP_BUILD_DIR}" 2>/dev/null || true' EXIT

  # Core files
  cp -a "${DOCKERFILE}" "${TMP_BUILD_DIR}/Dockerfile"
  cp -a "${ROOT_DIR}/requirements-trt.txt" "${TMP_BUILD_DIR}/requirements.txt"
  cp -a "${ROOT_DIR}/src" "${TMP_BUILD_DIR}/src"

  # Copy TRT scripts and common scripts (maintaining relative paths)
  mkdir -p "${TMP_BUILD_DIR}/scripts"
  cp -a "${SCRIPT_DIR}/scripts"/* "${TMP_BUILD_DIR}/scripts/"

  # Copy common scripts for runtime use
  mkdir -p "${TMP_BUILD_DIR}/common/scripts"
  cp -a "${SCRIPT_DIR}/../common/scripts"/* "${TMP_BUILD_DIR}/common/scripts/"

  # Copy download scripts - TRT-specific and common
  mkdir -p "${TMP_BUILD_DIR}/download"
  cp -a "${SCRIPT_DIR}/download"/* "${TMP_BUILD_DIR}/download/"

  # Copy common download utilities
  mkdir -p "${TMP_BUILD_DIR}/common/download"
  cp -a "${SCRIPT_DIR}/../common/download"/* "${TMP_BUILD_DIR}/common/download/"

  # Copy tests for warmup
  if [ -d "${ROOT_DIR}/tests" ]; then
    cp -a "${ROOT_DIR}/tests" "${TMP_BUILD_DIR}/tests"
  fi

  # shellcheck disable=SC2034  # consumed by parent build script after sourcing
  BUILD_CONTEXT="${TMP_BUILD_DIR}"
}
