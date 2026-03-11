#!/usr/bin/env bash
# install_security_tools - Install repo-local fallback copies of security scanners.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

# link_tool - Symlink a versioned binary into the shared repo-local bin directory.
link_tool() {
  local binary_path="$1"
  local tool_name="$2"
  ln -sf "${binary_path}" "$(repo_bin_dir)/${tool_name}"
}

# install_gitleaks - Download and install the configured Gitleaks CLI version.
install_gitleaks() {
  source_security_config "gitleaks"

  local os_name
  local arch_name
  local asset_name
  local release_url
  local tmp_dir
  local tool_root
  local version_dir
  local binary_path

  os_name="$(resolve_os "${GITLEAKS_OS_DARWIN}" "${GITLEAKS_OS_LINUX}" "${GITLEAKS_TOOL_NAME}")"
  arch_name="$(resolve_arch "${GITLEAKS_ARCH_AMD64}" "${GITLEAKS_ARCH_ARM64}" "${GITLEAKS_TOOL_NAME}")"
  asset_name="${GITLEAKS_ARCHIVE_PREFIX}_${GITLEAKS_VERSION}_${os_name}_${arch_name}.tar.gz"
  release_url="${GITLEAKS_RELEASE_BASE_URL}/v${GITLEAKS_VERSION}"
  tool_root="$(repo_tool_dir "${GITLEAKS_TOOL_NAME}")"
  version_dir="${tool_root}/${GITLEAKS_VERSION}"
  binary_path="${version_dir}/${GITLEAKS_TOOL_NAME}"

  if [[ -x ${binary_path} ]]; then
    link_tool "${binary_path}" "${GITLEAKS_TOOL_NAME}"
    echo "${binary_path}"
    return 0
  fi

  if ! command -v tar >/dev/null 2>&1; then
    echo "error: tar is required to install ${GITLEAKS_TOOL_NAME}" >&2
    exit 1
  fi

  tmp_dir="$(download_and_verify "${release_url}" "${asset_name}" "${GITLEAKS_ARCHIVE_PREFIX}_${GITLEAKS_VERSION}_${GITLEAKS_CHECKSUMS_SUFFIX}")"
  rm -rf "${version_dir}"
  mkdir -p "${version_dir}"
  tar -xzf "${tmp_dir}/${asset_name}" -C "${version_dir}"
  rm -rf "${tmp_dir}"

  if [[ ! -x ${binary_path} ]]; then
    echo "error: ${GITLEAKS_TOOL_NAME} binary missing after install" >&2
    exit 1
  fi

  link_tool "${binary_path}" "${GITLEAKS_TOOL_NAME}"
  echo "${binary_path}"
}

# install_bearer - Download and install the configured Bearer CLI version.
install_bearer() {
  source_security_config "bearer"

  local os_name
  local arch_name
  local asset_name
  local release_url
  local tmp_dir
  local tool_root
  local version_dir
  local binary_path

  os_name="$(resolve_os "${BEARER_OS_DARWIN}" "${BEARER_OS_LINUX}" "${BEARER_TOOL_NAME}")"
  arch_name="$(resolve_arch "${BEARER_ARCH_AMD64}" "${BEARER_ARCH_ARM64}" "${BEARER_TOOL_NAME}")"
  asset_name="${BEARER_ARCHIVE_PREFIX}_${BEARER_VERSION}_${os_name}_${arch_name}.tar.gz"
  release_url="${BEARER_RELEASE_BASE_URL}/v${BEARER_VERSION}"
  tool_root="$(repo_tool_dir "${BEARER_TOOL_NAME}")"
  version_dir="${tool_root}/${BEARER_VERSION}"
  binary_path="${version_dir}/${BEARER_TOOL_NAME}"

  if [[ -x ${binary_path} ]]; then
    link_tool "${binary_path}" "${BEARER_TOOL_NAME}"
    echo "${binary_path}"
    return 0
  fi

  if ! command -v tar >/dev/null 2>&1; then
    echo "error: tar is required to install ${BEARER_TOOL_NAME}" >&2
    exit 1
  fi

  tmp_dir="$(download_and_verify "${release_url}" "${asset_name}" "${BEARER_CHECKSUMS_FILE}")"
  rm -rf "${version_dir}"
  mkdir -p "${version_dir}"
  tar -xzf "${tmp_dir}/${asset_name}" -C "${version_dir}"
  rm -rf "${tmp_dir}"

  if [[ ! -x ${binary_path} ]]; then
    echo "error: ${BEARER_TOOL_NAME} binary missing after install" >&2
    exit 1
  fi

  link_tool "${binary_path}" "${BEARER_TOOL_NAME}"
  echo "${binary_path}"
}

# install_codeql - Download and install the configured CodeQL CLI version.
install_codeql() {
  source_security_config "codeql"

  local asset_name
  local checksum_name
  local release_url
  local tmp_dir
  local tool_root
  local version_dir
  local binary_path

  asset_name="$(resolve_os "${CODEQL_ARCHIVE_DARWIN}" "${CODEQL_ARCHIVE_LINUX}" "${CODEQL_TOOL_NAME}")"
  checksum_name="${asset_name}.checksum.txt"
  tool_root="$(repo_tool_dir "${CODEQL_INSTALL_SUBDIR}")"
  version_dir="${tool_root}/${CODEQL_VERSION}"
  binary_path="${version_dir}/${CODEQL_INSTALL_SUBDIR}/${CODEQL_TOOL_NAME}"

  if [[ -x ${binary_path} ]]; then
    link_tool "${binary_path}" "${CODEQL_TOOL_NAME}"
    echo "${binary_path}"
    return 0
  fi

  if ! command -v unzip >/dev/null 2>&1; then
    echo "error: unzip is required to install ${CODEQL_TOOL_NAME}" >&2
    exit 1
  fi

  release_url="${CODEQL_RELEASE_BASE_URL}/v${CODEQL_VERSION}"
  tmp_dir="$(download_and_verify "${release_url}" "${asset_name}" "${checksum_name}")"
  rm -rf "${version_dir}"
  mkdir -p "${version_dir}"
  unzip -q "${tmp_dir}/${asset_name}" -d "${version_dir}"
  rm -rf "${tmp_dir}"

  if [[ ! -x ${binary_path} ]]; then
    echo "error: ${CODEQL_TOOL_NAME} binary missing after install" >&2
    exit 1
  fi

  link_tool "${binary_path}" "${CODEQL_TOOL_NAME}"
  echo "${binary_path}"
}

# install_osv - Download and install the configured OSV-Scanner CLI version.
install_osv() {
  source_security_config "osv"

  local os_name
  local arch_name
  local asset_name
  local release_url
  local tmp_dir
  local tool_root
  local version_dir
  local binary_path

  os_name="$(resolve_os "${OSV_SCANNER_OS_DARWIN}" "${OSV_SCANNER_OS_LINUX}" "${OSV_SCANNER_TOOL_NAME}")"
  arch_name="$(resolve_arch "${OSV_SCANNER_ARCH_AMD64}" "${OSV_SCANNER_ARCH_ARM64}" "${OSV_SCANNER_TOOL_NAME}")"
  asset_name="${OSV_SCANNER_ASSET_PREFIX}_${os_name}_${arch_name}"
  release_url="${OSV_SCANNER_RELEASE_BASE_URL}/v${OSV_SCANNER_VERSION}"
  tool_root="$(repo_tool_dir "${OSV_SCANNER_TOOL_NAME}")"
  version_dir="${tool_root}/${OSV_SCANNER_VERSION}"
  binary_path="${version_dir}/${OSV_SCANNER_TOOL_NAME}"

  if [[ -x ${binary_path} ]]; then
    link_tool "${binary_path}" "${OSV_SCANNER_TOOL_NAME}"
    echo "${binary_path}"
    return 0
  fi

  tmp_dir="$(download_and_verify "${release_url}" "${asset_name}" "${OSV_SCANNER_CHECKSUMS_ASSET}")"
  rm -rf "${version_dir}"
  mkdir -p "${version_dir}"
  mv "${tmp_dir}/${asset_name}" "${binary_path}"
  chmod +x "${binary_path}"
  rm -rf "${tmp_dir}"

  link_tool "${binary_path}" "${OSV_SCANNER_TOOL_NAME}"
  echo "${binary_path}"
}

case "${1:-all}" in
  gitleaks)
    install_gitleaks
    ;;
  bearer)
    install_bearer
    ;;
  codeql)
    install_codeql
    ;;
  osv-scanner)
    install_osv
    ;;
  all)
    install_gitleaks >/dev/null
    install_bearer >/dev/null
    install_codeql >/dev/null
    install_osv >/dev/null
    ;;
  *)
    echo "usage: $0 [gitleaks|bearer|codeql|osv-scanner|all]" >&2
    exit 1
    ;;
esac
