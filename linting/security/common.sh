#!/usr/bin/env bash
# require_docker - Abort if Docker or the Docker daemon is unavailable.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SECURITY_CONFIG_DIR="${REPO_ROOT}/linting/config/security"

# source_security_config - Load a repo-local shell config file by name.
source_security_config() {
  local config_name="$1"
  local config_path="${SECURITY_CONFIG_DIR}/${config_name}.env"
  if [[ ! -f ${config_path} ]]; then
    echo "error: missing security config: ${config_path}" >&2
    exit 1
  fi

  # shellcheck disable=SC1090  # lint:justify -- reason: security wrappers intentionally source repo-local config files by path -- ticket: N/A
  source "${config_path}"
}

source_security_config "common"
source_security_config "tool-versions"

# require_docker - Abort if Docker or the Docker daemon is unavailable.
require_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "error: docker is required" >&2
    exit 1
  fi

  if ! docker info >/dev/null 2>&1; then
    echo "error: docker daemon unavailable" >&2
    exit 1
  fi
}

# require_tool - Abort if a local CLI tool is unavailable.
require_tool() {
  local tool="$1"
  if ! command -v "${tool}" >/dev/null 2>&1; then
    echo "error: ${tool} is required" >&2
    exit 1
  fi
}

# repo_cache_dir - Return the shared cache directory for dockerized scanners.
repo_cache_dir() {
  local cache_dir="${REPO_ROOT}/${SECURITY_CACHE_RELATIVE_DIR}"
  mkdir -p "${cache_dir}"
  echo "${cache_dir}"
}
