#!/usr/bin/env bash
# Shared Docker build driver for stack-specific entrypoints.

_BUILD_DRIVER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "${_BUILD_DRIVER_DIR}/docker.sh"
source "${_BUILD_DRIVER_DIR}/args.sh"
source "${_BUILD_DRIVER_DIR}/context.sh"
source "${_BUILD_DRIVER_DIR}/validate.sh"

# require_docker_username - Abort when the image namespace has not been configured.
require_docker_username() {
  if [[ ${DOCKER_USERNAME:-your-username} == "your-username" ]]; then
    log_err "[build] ✗ Please set DOCKER_USERNAME environment variable"
    log_info "[build] Example: DOCKER_USERNAME=myuser $0"
    exit 1
  fi
}

# validate_tag_prefix - Enforce the expected image tag prefix for a stack.
validate_tag_prefix() {
  local tag_value="$1"
  local tag_prefix="$2"
  local engine_label="$3"
  local example_tag="$4"

  if [[ ! ${tag_value} =~ ^${tag_prefix} ]]; then
    log_err "[build] ✗ TAG must start with '${tag_prefix}' for ${engine_label} images"
    log_info "[build]   Got: ${tag_value}"
    log_info "[build]   Example: ${example_tag}"
    exit 1
  fi
}

# finalize_image_name - Resolve and export the full Docker image name for the stack.
finalize_image_name() {
  FULL_IMAGE_NAME="${DOCKER_USERNAME}/${IMAGE_NAME}:${TAG}"
  export FULL_IMAGE_NAME
}

# run_stack_build - Execute the shared validate/build/push flow for one Docker stack.
run_stack_build() {
  local stack_dir="$1"
  local requirements_file="$2"
  local include_stack_download="$3"
  local tmp_prefix="$4"

  require_docker_username
  finalize_image_name

  if declare -F validate_stack_build >/dev/null 2>&1; then
    validate_stack_build
  fi
  echo

  require_docker
  ensure_docker_login

  log_info "[build] Building Docker image: ${FULL_IMAGE_NAME}..."
  if declare -F log_stack_build >/dev/null 2>&1; then
    log_stack_build
  fi

  prepare_build_context_common "${stack_dir}" "${requirements_file}" "${include_stack_download}" "${tmp_prefix}"
  init_build_args

  if declare -F append_stack_build_args >/dev/null 2>&1; then
    append_stack_build_args
  fi

  docker build "${BUILD_ARGS[@]}" "${BUILD_CONTEXT}"

  log_success "[build] ✓ Docker build complete"
  log_info "[build] Pushing to Docker Hub..."

  if ! docker push "${FULL_IMAGE_NAME}"; then
    log_warn "[build] ⚠ Initial docker push failed. Attempting non-interactive login and retry..."
    ensure_docker_login || true
    if ! docker push "${FULL_IMAGE_NAME}"; then
      log_err "[build] ✗ Docker push failed. Please run 'docker login' and ensure DOCKER_USERNAME has access to push ${FULL_IMAGE_NAME}."
      exit 1
    fi
  fi

  log_success "[build] ✓ Pushed ${FULL_IMAGE_NAME}"
}
