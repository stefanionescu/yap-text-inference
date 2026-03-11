#!/usr/bin/env bash
# run_osv - Run OSV-Scanner against the repository source tree.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../common.sh
source "${SCRIPT_DIR}/../common.sh"
source_security_config "osv"

cd "${REPO_ROOT}"

# resolve_osv_command - Resolve the local, cached, or auto-installed OSV-Scanner binary.
resolve_osv_command() {
  local cached_binary="${REPO_ROOT}/${SECURITY_CACHE_RELATIVE_DIR}/bin/${OSV_SCANNER_TOOL_NAME}"

  if command -v "${OSV_SCANNER_TOOL_NAME}" >/dev/null 2>&1; then
    command -v "${OSV_SCANNER_TOOL_NAME}"
    return 0
  fi
  if [[ -x ${cached_binary} ]]; then
    echo "${cached_binary}"
    return 0
  fi
  if bash "${REPO_ROOT}/linting/security/install.sh" "${OSV_SCANNER_TOOL_NAME}" >/dev/null 2>&1 && [[ -x ${cached_binary} ]]; then
    echo "${cached_binary}"
    return 0
  fi
  return 1
}

if OSV_COMMAND="$(resolve_osv_command)"; then
  "${OSV_COMMAND}" "${OSV_SCAN_ARGS[@]}" "${OSV_SCAN_ROOT}"
  exit 0
fi

require_docker
docker run --rm \
  -v "${REPO_ROOT}:/src" \
  "${OSV_SCANNER_IMAGE}" \
  "${OSV_SCAN_ARGS[@]}" /src
