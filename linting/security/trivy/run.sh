#!/usr/bin/env bash
# run_trivy - Run Trivy config/filesystem/image scans for this repository.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../common.sh
source "${SCRIPT_DIR}/../common.sh"
source_security_config "trivy"

MODE="${1:-all}"

# run_trivy_local - Run Trivy locally when the CLI is installed.
run_trivy_local() {
  local mode="$1"
  case "${mode}" in
    config)
      trivy config --exit-code 1 --ignorefile "${TRIVY_IGNORE_FILE}" "${TRIVY_CONFIG_TARGETS[@]}"
      ;;
    fs)
      trivy fs --exit-code 1 --ignorefile "${TRIVY_IGNORE_FILE}" "${TRIVY_FS_TARGET}"
      ;;
    all)
      run_trivy_local config
      run_trivy_local fs
      ;;
    *)
      echo "usage: $0 [config|fs|all]" >&2
      exit 1
      ;;
  esac
}

# run_trivy_docker - Run Trivy inside Docker when the CLI is unavailable.
run_trivy_docker() {
  local mode="$1"
  local cache_dir
  cache_dir="$(repo_cache_dir)"

  case "${mode}" in
    config)
      docker run --rm \
        -v "${REPO_ROOT}:/workspace:ro" \
        -v "${cache_dir}:/root/.cache" \
        "${TRIVY_IMAGE}" \
        config --exit-code 1 --ignorefile "/workspace/${TRIVY_IGNORE_FILE}" /workspace/docker
      ;;
    fs)
      docker run --rm \
        -v "${REPO_ROOT}:/workspace:ro" \
        -v "${cache_dir}:/root/.cache" \
        "${TRIVY_IMAGE}" \
        fs --exit-code 1 --ignorefile "/workspace/${TRIVY_IGNORE_FILE}" /workspace
      ;;
    all)
      run_trivy_docker config
      run_trivy_docker fs
      ;;
    *)
      echo "usage: $0 [config|fs|all]" >&2
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
