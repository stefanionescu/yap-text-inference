#!/usr/bin/env bash
# Build context preparation for vLLM Docker images.
#
# Creates a temporary directory with all files needed for the Docker build,
# including shared utilities from common/ and vLLM-specific download scripts.

prepare_build_context() {
  TMP_BUILD_DIR="$(mktemp -d -t yap-vllm-build-XXXXXX)"
  trap 'rm -rf "${TMP_BUILD_DIR}" 2>/dev/null || true' EXIT

  # Core files
  cp -a "${DOCKERFILE}" "${TMP_BUILD_DIR}/Dockerfile"
  cp -a "${SCRIPT_DIR}/.dockerignore" "${TMP_BUILD_DIR}/.dockerignore"
  cp -a "${ROOT_DIR}/requirements-vllm.txt" "${TMP_BUILD_DIR}/requirements.txt"
  cp -a "${ROOT_DIR}/src" "${TMP_BUILD_DIR}/src"

  # Copy vLLM scripts and common scripts (maintaining relative paths)
  mkdir -p "${TMP_BUILD_DIR}/scripts"
  cp -a "${SCRIPT_DIR}/scripts"/* "${TMP_BUILD_DIR}/scripts/"

  # Copy common runtime scripts (no download utils - those are build-time only)
  mkdir -p "${TMP_BUILD_DIR}/common/scripts"
  cp -a "${SCRIPT_DIR}/../common/scripts"/* "${TMP_BUILD_DIR}/common/scripts/"

  # Copy download scripts - vLLM-specific and common (used during docker build only)
  mkdir -p "${TMP_BUILD_DIR}/download"
  cp -a "${SCRIPT_DIR}/download"/* "${TMP_BUILD_DIR}/download/"
  mkdir -p "${TMP_BUILD_DIR}/common/download"
  cp -a "${SCRIPT_DIR}/../common/download"/* "${TMP_BUILD_DIR}/common/download/"

  # shellcheck disable=SC2034  # consumed by parent build script after sourcing
  BUILD_CONTEXT="${TMP_BUILD_DIR}"
}
