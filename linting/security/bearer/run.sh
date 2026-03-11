#!/usr/bin/env bash
# run_bearer - Run Bearer CLI against the repository source tree.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../common.sh
source "${SCRIPT_DIR}/../common.sh"
source_security_config "bearer"

cd "${REPO_ROOT}"

# resolve_bearer_command - Resolve the local, cached, or auto-installed Bearer binary.
resolve_bearer_command() {
  local cached_binary="${REPO_ROOT}/${SECURITY_CACHE_RELATIVE_DIR}/bin/${BEARER_TOOL_NAME}"

  if command -v "${BEARER_TOOL_NAME}" >/dev/null 2>&1; then
    command -v "${BEARER_TOOL_NAME}"
    return 0
  fi
  if [[ -x ${cached_binary} ]]; then
    echo "${cached_binary}"
    return 0
  fi
  if bash "${REPO_ROOT}/linting/security/install.sh" "${BEARER_TOOL_NAME}" >/dev/null 2>&1 && [[ -x ${cached_binary} ]]; then
    echo "${cached_binary}"
    return 0
  fi
  return 1
}

if BEARER_COMMAND="$(resolve_bearer_command)"; then
  "${BEARER_COMMAND}" scan "${BEARER_FLAGS[@]}" "${BEARER_SCAN_ROOT}" --config-file "${BEARER_CONFIG_FILE}"
  exit 0
fi

require_docker
docker run --rm \
  -v "${REPO_ROOT}:/workspace" \
  "${BEARER_IMAGE}" \
  scan "${BEARER_FLAGS[@]}" /workspace --config-file "/workspace/${BEARER_CONFIG_FILE}"
