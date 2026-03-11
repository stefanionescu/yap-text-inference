#!/usr/bin/env bash
# run_osv - Run OSV-Scanner against the repository source tree.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../common.sh
source "${SCRIPT_DIR}/../common.sh"
source_security_config "osv"

cd "${REPO_ROOT}"

if command -v "${OSV_SCANNER_TOOL_NAME}" >/dev/null 2>&1; then
  "${OSV_SCANNER_TOOL_NAME}" "${OSV_SCAN_ARGS[@]}" "${OSV_SCAN_ROOT}"
  exit 0
fi

require_docker
docker run --rm \
  -v "${REPO_ROOT}:/src" \
  "${OSV_SCANNER_IMAGE}" \
  "${OSV_SCAN_ARGS[@]}" /src
