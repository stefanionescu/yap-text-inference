#!/usr/bin/env bash
# require_docker - Abort if Docker or the Docker daemon is unavailable.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SECURITY_CONFIG_DIR="${REPO_ROOT}/linting/config/security"

# source_security_config - Load a repo-local shell config file by name.
source_security_config() {
  local config_name="$1"
  local config_path="${SECURITY_CONFIG_DIR}/${config_name}"
  if [[ -f ${config_path} ]]; then
    :
  elif [[ -f ${config_path}.env ]]; then
    config_path="${config_path}.env"
  elif [[ -f ${config_path}/env.sh ]]; then
    config_path="${config_path}/env.sh"
  fi
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

# require_download_command - Abort if curl is unavailable for fallback installs.
require_download_command() {
  if ! command -v curl >/dev/null 2>&1; then
    echo "error: curl is required for fallback security tool installation" >&2
    exit 1
  fi
}

# repo_cache_dir - Return the shared cache directory for dockerized scanners.
repo_cache_dir() {
  local cache_dir="${REPO_ROOT}/${SECURITY_CACHE_RELATIVE_DIR}"
  mkdir -p "${cache_dir}"
  echo "${cache_dir}"
}

# repo_bin_dir - Return the repo-local directory for installed fallback binaries.
repo_bin_dir() {
  local bin_dir
  bin_dir="$(repo_cache_dir)/bin"
  mkdir -p "${bin_dir}"
  echo "${bin_dir}"
}

# repo_tool_dir - Return the repo-local directory for a named fallback tool.
repo_tool_dir() {
  local tool_name="$1"
  local tool_dir
  tool_dir="$(repo_cache_dir)/${tool_name}"
  mkdir -p "${tool_dir}"
  echo "${tool_dir}"
}

# resolve_tool_command - Resolve a system, cached, or auto-installed tool binary.
resolve_tool_command() {
  local tool_name="$1"
  local install_target="${2:-$1}"
  local cached_binary="${REPO_ROOT}/${SECURITY_CACHE_RELATIVE_DIR}/bin/${tool_name}"

  if command -v "${tool_name}" >/dev/null 2>&1; then
    command -v "${tool_name}"
    return 0
  fi
  if [[ -x ${cached_binary} ]]; then
    echo "${cached_binary}"
    return 0
  fi
  if bash "${REPO_ROOT}/linting/security/install.sh" "${install_target}" >/dev/null 2>&1 && [[ -x ${cached_binary} ]]; then
    echo "${cached_binary}"
    return 0
  fi
  return 1
}

# resolve_required_tool_command - Resolve a tool binary or abort with a clear error.
resolve_required_tool_command() {
  local tool_name="$1"
  local install_target="${2:-$1}"
  local resolved

  if resolved="$(resolve_tool_command "${tool_name}" "${install_target}")"; then
    echo "${resolved}"
    return 0
  fi

  echo "error: unable to resolve ${tool_name}" >&2
  exit 1
}

# sha256_file - Compute the SHA-256 hash for a file.
sha256_file() {
  local path="$1"
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "${path}" | awk '{print $1}'
    return 0
  fi
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "${path}" | awk '{print $1}'
    return 0
  fi
  if command -v openssl >/dev/null 2>&1; then
    openssl dgst -sha256 "${path}" | awk '{print $NF}'
    return 0
  fi
  echo "error: unable to compute sha256" >&2
  exit 1
}

# resolve_os - Return a Darwin or Linux asset value for the current platform.
resolve_os() {
  local darwin_value="$1"
  local linux_value="$2"
  local tool_name="$3"
  local uname_s
  uname_s="$(uname -s | tr '[:upper:]' '[:lower:]')"

  case "${uname_s}" in
    darwin)
      echo "${darwin_value}"
      ;;
    linux)
      echo "${linux_value}"
      ;;
    *)
      echo "error: unsupported OS for ${tool_name}: ${uname_s}" >&2
      exit 1
      ;;
  esac
}

# resolve_arch - Return an amd64 or arm64 asset value for the current platform.
resolve_arch() {
  local amd64_value="$1"
  local arm64_value="$2"
  local tool_name="$3"
  local uname_m
  uname_m="$(uname -m)"

  case "${uname_m}" in
    x86_64 | amd64)
      echo "${amd64_value}"
      ;;
    arm64 | aarch64)
      echo "${arm64_value}"
      ;;
    *)
      echo "error: unsupported architecture for ${tool_name}: ${uname_m}" >&2
      exit 1
      ;;
  esac
}

# download_and_verify - Download an asset and checksum file, then verify the checksum.
download_and_verify() {
  local base_url="$1"
  local asset_name="$2"
  local checksum_name="$3"
  local tmp_dir
  local asset_path
  local checksum_path
  local expected_sha
  local actual_sha

  require_download_command
  tmp_dir="$(mktemp -d)"
  asset_path="${tmp_dir}/${asset_name}"
  checksum_path="${tmp_dir}/${checksum_name}"

  curl -fsSL "${base_url}/${asset_name}" -o "${asset_path}"
  curl -fsSL "${base_url}/${checksum_name}" -o "${checksum_path}"

  expected_sha="$(awk -v target="${asset_name}" '$2==target { print $1 }' "${checksum_path}")"
  if [[ -z ${expected_sha} ]]; then
    expected_sha="$(awk 'NF { print $1; exit }' "${checksum_path}")"
  fi
  if [[ -z ${expected_sha} ]]; then
    echo "error: checksum entry missing for ${asset_name}" >&2
    rm -rf "${tmp_dir}"
    exit 1
  fi

  actual_sha="$(sha256_file "${asset_path}")"
  if [[ ${actual_sha} != "${expected_sha}" ]]; then
    echo "error: checksum mismatch for ${asset_name}" >&2
    echo "expected: ${expected_sha}" >&2
    echo "actual:   ${actual_sha}" >&2
    rm -rf "${tmp_dir}"
    exit 1
  fi

  echo "${tmp_dir}"
}
