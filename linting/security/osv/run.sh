#!/usr/bin/env bash
# run_osv - Run OSV-Scanner against the repository source tree.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../common.sh
source "${SCRIPT_DIR}/../common.sh"
source_security_config "osv.env"

cd "${REPO_ROOT}"

if OSV_COMMAND="$(resolve_tool_command "${OSV_SCANNER_TOOL_NAME}")"; then
  "${OSV_COMMAND}" "${OSV_SCAN_ARGS[@]}" "${OSV_SCAN_ROOT}"
  exit 0
fi

require_docker
docker run --rm \
  -v "${REPO_ROOT}:/src" \
  "${OSV_SCANNER_IMAGE}" \
  "${OSV_SCAN_ARGS[@]}" /src
