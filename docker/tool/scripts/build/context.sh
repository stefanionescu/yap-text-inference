#!/usr/bin/env bash
# Build context preparation for tool-only Docker images.
#
# Creates a temporary directory with all files needed for the Docker build.
# No engine-specific download scripts needed -- only the common tool downloader.

prepare_build_context() {
  TMP_BUILD_DIR="$(mktemp -d -t yap-tool-build-XXXXXX)"
  trap 'rm -rf "${TMP_BUILD_DIR}" 2>/dev/null || true' EXIT

  # Core files
  cp -a "${DOCKERFILE}" "${TMP_BUILD_DIR}/Dockerfile"
  cp -a "${SCRIPT_DIR}/.dockerignore" "${TMP_BUILD_DIR}/.dockerignore"
  cp -a "${ROOT_DIR}/requirements-tool.txt" "${TMP_BUILD_DIR}/requirements.txt"
  cp -a "${ROOT_DIR}/src" "${TMP_BUILD_DIR}/src"

  # Copy tool scripts and common scripts (maintaining relative paths)
  mkdir -p "${TMP_BUILD_DIR}/scripts"
  cp -a "${SCRIPT_DIR}/scripts"/* "${TMP_BUILD_DIR}/scripts/"

  # Copy common runtime scripts
  mkdir -p "${TMP_BUILD_DIR}/common/scripts"
  cp -a "${SCRIPT_DIR}/../common/scripts"/* "${TMP_BUILD_DIR}/common/scripts/"

  # Copy common download scripts (tool model downloader only, no engine-specific download/)
  mkdir -p "${TMP_BUILD_DIR}/common/download"
  cp -a "${SCRIPT_DIR}/../common/download"/* "${TMP_BUILD_DIR}/common/download/"

  # shellcheck disable=SC2034  # consumed by parent build script after sourcing
  BUILD_CONTEXT="${TMP_BUILD_DIR}"
}
