#!/usr/bin/env bash
# run_bearer - Run Bearer CLI against the repository source tree.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../common.sh
source "${SCRIPT_DIR}/../common.sh"
source_security_config "bearer"

cd "${REPO_ROOT}"

if command -v bearer >/dev/null 2>&1; then
  bearer scan . --config-file "${BEARER_CONFIG_FILE}"
  exit 0
fi

require_docker
docker run --rm \
  -v "${REPO_ROOT}:/workspace" \
  "${BEARER_IMAGE}" \
  scan /workspace --config-file "/workspace/${BEARER_CONFIG_FILE}"
