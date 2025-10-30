#!/usr/bin/env bash

prepare_build_context() {
  TMP_BUILD_DIR="$(mktemp -d -t yap-awq-build-XXXXXX)"
  cleanup() { rm -rf "${TMP_BUILD_DIR}" 2>/dev/null || true; }
  trap cleanup EXIT

  cp -a "${DOCKERFILE}" "${TMP_BUILD_DIR}/Dockerfile"
  cp -a "${SCRIPT_DIR}/scripts" "${TMP_BUILD_DIR}/scripts"
  cp -a "${ROOT_DIR}/requirements.txt" "${TMP_BUILD_DIR}/requirements.txt"
  cp -a "${ROOT_DIR}/prompts" "${TMP_BUILD_DIR}/prompts"
  cp -a "${ROOT_DIR}/src" "${TMP_BUILD_DIR}/src"

  BUILD_CONTEXT="${TMP_BUILD_DIR}"
}


