#!/usr/bin/env bash

prepare_build_context() {
  TMP_BUILD_DIR="$(mktemp -d -t yap-base-build-XXXXXX)"
  trap 'rm -rf "${TMP_BUILD_DIR}" 2>/dev/null || true' EXIT

  cp -a "${DOCKERFILE}" "${TMP_BUILD_DIR}/Dockerfile"
  cp -a "${SCRIPT_DIR}/scripts" "${TMP_BUILD_DIR}/scripts"
  cp -a "${ROOT_DIR}/requirements.txt" "${TMP_BUILD_DIR}/requirements.txt"
  cp -a "${ROOT_DIR}/src" "${TMP_BUILD_DIR}/src"
  cp -a "${ROOT_DIR}/prompts" "${TMP_BUILD_DIR}/prompts"
  cp -a "${ROOT_DIR}/test" "${TMP_BUILD_DIR}/test"
}


