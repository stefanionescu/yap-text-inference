#!/usr/bin/env bash
# run_bearer - Run Bearer CLI against the repository source tree.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../common.sh
source "${SCRIPT_DIR}/../common.sh"
source_security_config "bearer.env"

cd "${REPO_ROOT}"

if BEARER_COMMAND="$(resolve_tool_command "${BEARER_TOOL_NAME}")"; then
  "${BEARER_COMMAND}" scan "${BEARER_FLAGS[@]}" "${BEARER_SCAN_ROOT}" --config-file "${BEARER_CONFIG_FILE}"
  exit 0
fi

require_docker
docker run --rm \
  -v "${REPO_ROOT}:/workspace" \
  "${BEARER_IMAGE}" \
  scan "${BEARER_FLAGS[@]}" /workspace --config-file "/workspace/${BEARER_CONFIG_FILE}"
