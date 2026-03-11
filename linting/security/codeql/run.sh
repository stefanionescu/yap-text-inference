#!/usr/bin/env bash
# run_codeql - Run a CodeQL scan for this repository.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
# shellcheck source=../common.sh
source "${SCRIPT_DIR}/../common.sh"
source_security_config "codeql"

# resolve_repo_path - Resolve a repo-relative path while preserving absolute inputs.
resolve_repo_path() {
  local value="$1"
  if [[ ${value} == /* ]]; then
    echo "${value}"
    return 0
  fi
  echo "${REPO_ROOT}/${value}"
}

RESULT_FILE="$(resolve_repo_path "${CODEQL_OUTPUT_FILE:-${CODEQL_RESULT_FILE}}")"

bash "${SCRIPT_DIR}/scan.sh"
echo "codeql sarif: ${RESULT_FILE}"
