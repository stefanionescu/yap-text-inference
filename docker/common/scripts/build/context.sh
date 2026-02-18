#!/usr/bin/env bash
# Shared Docker build-context preparation.
#
# Creates a temporary build context containing only runtime assets needed by
# the selected Docker stack.

prepare_build_context_common() {
  local stack_dir="$1"
  local requirements_file="$2"
  local include_stack_download="${3:-0}"
  local tmp_prefix="${4:-yap-docker}"

  TMP_BUILD_DIR="$(mktemp -d -t "${tmp_prefix}-build-XXXXXX")"
  trap 'rm -rf "${TMP_BUILD_DIR}" 2>/dev/null || true' EXIT

  # Core files
  cp -a "${DOCKERFILE}" "${TMP_BUILD_DIR}/Dockerfile"
  cp -a "${stack_dir}/.dockerignore" "${TMP_BUILD_DIR}/.dockerignore"
  cp -a "${ROOT_DIR}/${requirements_file}" "${TMP_BUILD_DIR}/requirements.txt"
  cp -a "${ROOT_DIR}/src" "${TMP_BUILD_DIR}/src"

  # Stack runtime scripts
  mkdir -p "${TMP_BUILD_DIR}/scripts"
  cp -a "${stack_dir}/scripts"/* "${TMP_BUILD_DIR}/scripts/"

  # Shared Docker runtime scripts
  mkdir -p "${TMP_BUILD_DIR}/common/scripts"
  cp -a "${ROOT_DIR}/docker/common/scripts"/* "${TMP_BUILD_DIR}/common/scripts/"

  # Shared Docker download scripts (used only at build time inside Dockerfile)
  mkdir -p "${TMP_BUILD_DIR}/common/download"
  cp -a "${ROOT_DIR}/docker/common/download"/* "${TMP_BUILD_DIR}/common/download/"

  # Stack-specific download scripts (engine stacks only)
  if [ "${include_stack_download}" = "1" ]; then
    mkdir -p "${TMP_BUILD_DIR}/download"
    cp -a "${stack_dir}/download"/* "${TMP_BUILD_DIR}/download/"
  fi

  # shellcheck disable=SC2034  # consumed by parent build script after sourcing
  BUILD_CONTEXT="${TMP_BUILD_DIR}"
}
