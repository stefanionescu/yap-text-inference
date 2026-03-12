#!/usr/bin/env bash
# run_trivy - Run Trivy config/filesystem/image scans for this repository.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../common.sh
source "${SCRIPT_DIR}/../common.sh"
source_security_config "trivy.env"

MODE="${1:-all}"
BUILT_TRIVY_IMAGES=()

# cleanup_trivy_images - Remove temporary scan images created during this run.
cleanup_trivy_images() {
  local image_tag

  if [[ ${#BUILT_TRIVY_IMAGES[@]} -eq 0 ]] || ! command -v docker >/dev/null 2>&1; then
    return 0
  fi

  for image_tag in "${BUILT_TRIVY_IMAGES[@]}"; do
    docker image rm -f "${image_tag}" >/dev/null 2>&1 || true
  done
}
trap cleanup_trivy_images EXIT

# docker_workspace_paths - Convert repo-relative scan targets into docker-mounted workspace paths.
docker_workspace_paths() {
  local target
  for target in "$@"; do
    echo "/workspace/${target}"
  done
}

# create_build_context - Prepare a minimal Docker build context for a stack-local image scan.
create_build_context() {
  local stack_dir="$1"
  local requirements_file="$2"
  local include_stack_download="$3"
  local stack_name="$4"
  local build_dir

  build_dir="$(mktemp -d -t "yap-trivy-${stack_name}-XXXXXX")"
  cp -a "${REPO_ROOT}/${stack_dir}/Dockerfile" "${build_dir}/Dockerfile"
  cp -a "${REPO_ROOT}/${stack_dir}/.dockerignore" "${build_dir}/.dockerignore"
  cp -a "${REPO_ROOT}/${requirements_file}" "${build_dir}/requirements.txt"
  cp -a "${REPO_ROOT}/src" "${build_dir}/src"

  mkdir -p "${build_dir}/scripts"
  cp -a "${REPO_ROOT}/${stack_dir}/scripts/." "${build_dir}/scripts/"

  mkdir -p "${build_dir}/common/scripts"
  cp -a "${REPO_ROOT}/docker/common/scripts/." "${build_dir}/common/scripts/"

  mkdir -p "${build_dir}/common/download"
  cp -a "${REPO_ROOT}/docker/common/download/." "${build_dir}/common/download/"

  if [[ ${include_stack_download} == "1" ]]; then
    mkdir -p "${build_dir}/download"
    cp -a "${REPO_ROOT}/${stack_dir}/download/." "${build_dir}/download/"
  fi

  echo "${build_dir}"
}

# build_trivy_images - Build scan-only local images for each configured Docker stack.
build_trivy_images() {
  local spec
  local stack_name
  local stack_dir
  local requirements_file
  local include_stack_download
  local image_tag
  local build_args_csv
  local build_dir
  local build_arg
  local build_arg_entries=()
  local docker_args=()

  require_docker

  for spec in "${TRIVY_IMAGE_TARGET_SPECS[@]}"; do
    IFS='|' read -r stack_name stack_dir requirements_file include_stack_download image_tag build_args_csv <<<"${spec}"

    docker_args=()
    if [[ -n ${build_args_csv} ]]; then
      IFS=',' read -r -a build_arg_entries <<<"${build_args_csv}"
      for build_arg in "${build_arg_entries[@]}"; do
        docker_args+=(--build-arg "${build_arg}")
      done
    fi
    docker_args+=(--platform "${TRIVY_DOCKER_PLATFORM}")

    build_dir="$(create_build_context "${stack_dir}" "${requirements_file}" "${include_stack_download}" "${stack_name}")"
    docker build -t "${image_tag}" "${docker_args[@]}" "${build_dir}"
    rm -rf "${build_dir}"
    BUILT_TRIVY_IMAGES+=("${image_tag}")
  done
}

# run_trivy_local - Run Trivy locally when the CLI is installed.
run_trivy_local() {
  local mode="$1"
  local config_target
  local image_tag

  case "${mode}" in
    config)
      for config_target in "${TRIVY_CONFIG_TARGETS[@]}"; do
        trivy config --exit-code 1 --ignorefile "${TRIVY_IGNORE_FILE}" "${config_target}"
      done
      ;;
    fs)
      trivy fs --exit-code 1 --ignorefile "${TRIVY_IGNORE_FILE}" "${TRIVY_FS_TARGET}"
      ;;
    image)
      build_trivy_images
      for image_tag in "${BUILT_TRIVY_IMAGES[@]}"; do
        trivy image --exit-code 1 --ignorefile "${TRIVY_IGNORE_FILE}" "${image_tag}"
      done
      ;;
    all)
      run_trivy_local config
      run_trivy_local fs
      run_trivy_local image
      ;;
    *)
      echo "usage: $0 [config|fs|image|all]" >&2
      exit 1
      ;;
  esac
}

# run_trivy_docker - Run Trivy inside Docker when the CLI is unavailable.
run_trivy_docker() {
  local mode="$1"
  local cache_dir
  local docker_target
  local image_tag

  cache_dir="$(tool_cache_dir)"

  case "${mode}" in
    config)
      while IFS= read -r docker_target; do
        docker run --rm \
          -v "${REPO_ROOT}:/workspace:ro" \
          -v "${cache_dir}:/root/.cache" \
          "${TRIVY_IMAGE}" \
          config --exit-code 1 --ignorefile "/workspace/${TRIVY_IGNORE_FILE}" "${docker_target}"
      done < <(docker_workspace_paths "${TRIVY_CONFIG_TARGETS[@]}")
      ;;
    fs)
      docker run --rm \
        -v "${REPO_ROOT}:/workspace:ro" \
        -v "${cache_dir}:/root/.cache" \
        "${TRIVY_IMAGE}" \
        fs --exit-code 1 --ignorefile "/workspace/${TRIVY_IGNORE_FILE}" /workspace
      ;;
    image)
      build_trivy_images
      for image_tag in "${BUILT_TRIVY_IMAGES[@]}"; do
        docker run --rm \
          -v /var/run/docker.sock:/var/run/docker.sock \
          -v "${REPO_ROOT}:/workspace:ro" \
          -v "${cache_dir}:/root/.cache" \
          "${TRIVY_IMAGE}" \
          image --exit-code 1 --ignorefile "/workspace/${TRIVY_IGNORE_FILE}" "${image_tag}"
      done
      ;;
    all)
      run_trivy_docker config
      run_trivy_docker fs
      run_trivy_docker image
      ;;
    *)
      echo "usage: $0 [config|fs|image|all]" >&2
      exit 1
      ;;
  esac
}

cd "${REPO_ROOT}"

if command -v trivy >/dev/null 2>&1; then
  run_trivy_local "${MODE}"
  exit 0
fi

require_docker
run_trivy_docker "${MODE}"
