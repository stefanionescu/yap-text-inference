#!/usr/bin/env bash
# install_linting_tools - Install repo-local fallback copies of linting CLIs.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

# install_shfmt - Download and install the configured shfmt CLI version.
install_shfmt() {
  local os_name
  local arch_name
  local asset_name
  local release_url
  local tmp_dir
  local tool_root
  local version_dir
  local binary_path

  os_name="$(resolve_os "darwin" "linux" "shfmt")"
  arch_name="$(resolve_arch "amd64" "arm64" "shfmt")"
  asset_name="shfmt_v${SHFMT_VERSION}_${os_name}_${arch_name}"
  release_url="https://github.com/mvdan/sh/releases/download/v${SHFMT_VERSION}"
  tool_root="$(tool_dir "shfmt")"
  version_dir="${tool_root}/${SHFMT_VERSION}"
  binary_path="${version_dir}/shfmt"

  if [[ -x ${binary_path} ]]; then
    link_tool "${binary_path}" "shfmt"
    echo "${binary_path}"
    return 0
  fi

  tmp_dir="$(download_and_verify "${release_url}" "${asset_name}" "sha256sums.txt")"
  rm -rf "${version_dir}"
  mkdir -p "${version_dir}"
  cp "${tmp_dir}/${asset_name}" "${binary_path}"
  chmod +x "${binary_path}"
  rm -rf "${tmp_dir}"

  if [[ ! -x ${binary_path} ]]; then
    echo "error: shfmt binary missing after install" >&2
    exit 1
  fi

  link_tool "${binary_path}" "shfmt"
  echo "${binary_path}"
}

# install_hadolint - Download and install the configured hadolint CLI version.
install_hadolint() {
  local os_name
  local arch_name
  local asset_name
  local release_url
  local tmp_dir
  local tool_root
  local version_dir
  local binary_path

  os_name="$(resolve_os "macos" "linux" "hadolint")"
  arch_name="$(resolve_arch "x86_64" "arm64" "hadolint")"
  asset_name="hadolint-${os_name}-${arch_name}"
  release_url="https://github.com/hadolint/hadolint/releases/download/v${HADOLINT_VERSION}"
  tool_root="$(tool_dir "hadolint")"
  version_dir="${tool_root}/${HADOLINT_VERSION}"
  binary_path="${version_dir}/hadolint"

  if [[ -x ${binary_path} ]]; then
    link_tool "${binary_path}" "hadolint"
    echo "${binary_path}"
    return 0
  fi

  tmp_dir="$(download_and_verify "${release_url}" "${asset_name}" "${asset_name}.sha256")"
  rm -rf "${version_dir}"
  mkdir -p "${version_dir}"
  cp "${tmp_dir}/${asset_name}" "${binary_path}"
  chmod +x "${binary_path}"
  rm -rf "${tmp_dir}"

  if [[ ! -x ${binary_path} ]]; then
    echo "error: hadolint binary missing after install" >&2
    exit 1
  fi

  link_tool "${binary_path}" "hadolint"
  echo "${binary_path}"
}

# install_gitlint - Install gitlint into an isolated repo-local virtualenv.
install_gitlint() {
  local tool_root
  local version_dir
  local venv_dir
  local binary_path
  local version_marker
  local version_spec

  if ! command -v python3 >/dev/null 2>&1; then
    echo "error: python3 is required to install gitlint" >&2
    exit 1
  fi

  tool_root="$(tool_dir "gitlint")"
  version_dir="${tool_root}/${GITLINT_VERSION}"
  venv_dir="${version_dir}/venv"
  binary_path="${venv_dir}/bin/gitlint"
  version_marker="${version_dir}/.package-version"
  version_spec="gitlint==${GITLINT_VERSION}"

  if [[ -x ${binary_path} && -f ${version_marker} && "$(<"${version_marker}")" == "${version_spec}" ]]; then
    link_tool "${binary_path}" "gitlint"
    echo "${binary_path}"
    return 0
  fi

  rm -rf "${version_dir}"
  mkdir -p "${version_dir}"
  python3 -m venv "${venv_dir}"
  "${venv_dir}/bin/python" -m pip install --disable-pip-version-check "${version_spec}"
  printf '%s\n' "${version_spec}" >"${version_marker}"

  if [[ ! -x ${binary_path} ]]; then
    echo "error: gitlint binary missing after install" >&2
    exit 1
  fi

  link_tool "${binary_path}" "gitlint"
  echo "${binary_path}"
}

# install_semgrep - Install Semgrep into an isolated repo-local virtualenv.
install_semgrep() {
  local tool_root
  local version_dir
  local venv_dir
  local binary_path
  local version_marker
  local version_spec

  if ! command -v python3 >/dev/null 2>&1; then
    echo "error: python3 is required to install semgrep" >&2
    exit 1
  fi

  tool_root="$(tool_dir "semgrep")"
  version_dir="${tool_root}/${SEMGREP_VERSION}"
  venv_dir="${version_dir}/venv"
  binary_path="${venv_dir}/bin/semgrep"
  version_marker="${version_dir}/.package-version"
  version_spec="semgrep==${SEMGREP_VERSION}"

  if [[ -x ${binary_path} && -f ${version_marker} && "$(<"${version_marker}")" == "${version_spec}" ]]; then
    # Semgrep used to live under the security cache; drop the old link so tooling owns resolution.
    rm -f "${REPO_ROOT}/.cache/security/bin/semgrep"
    link_tool "${binary_path}" "semgrep"
    echo "${binary_path}"
    return 0
  fi

  rm -rf "${version_dir}"
  mkdir -p "${version_dir}"
  python3 -m venv "${venv_dir}"
  "${venv_dir}/bin/python" -m pip install --disable-pip-version-check "${version_spec}"
  printf '%s\n' "${version_spec}" >"${version_marker}"

  if [[ ! -x ${binary_path} ]]; then
    echo "error: semgrep binary missing after install" >&2
    exit 1
  fi

  # Semgrep used to live under the security cache; drop the old link so tooling owns resolution.
  rm -f "${REPO_ROOT}/.cache/security/bin/semgrep"
  link_tool "${binary_path}" "semgrep"
  echo "${binary_path}"
}

case "${1:-all}" in
  shfmt)
    install_shfmt
    ;;
  hadolint)
    install_hadolint
    ;;
  gitlint)
    install_gitlint
    ;;
  semgrep)
    install_semgrep
    ;;
  all)
    install_shfmt >/dev/null
    install_hadolint >/dev/null
    install_gitlint >/dev/null
    install_semgrep >/dev/null
    ;;
  *)
    echo "usage: $0 [shfmt|hadolint|gitlint|semgrep|all]" >&2
    exit 1
    ;;
esac
