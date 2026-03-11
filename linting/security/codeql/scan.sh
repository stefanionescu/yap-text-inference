#!/usr/bin/env bash
# scan_codeql - Create and analyze a local CodeQL database for Python sources.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
# shellcheck source=../common.sh
source "${SCRIPT_DIR}/../common.sh"
source_security_config "codeql"

DB_DIR="${REPO_ROOT}/${CODEQL_DATABASE_DIR}"
RESULT_FILE="${REPO_ROOT}/${CODEQL_RESULT_FILE}"

if ! command -v "${CODEQL_TOOL_NAME}" >/dev/null 2>&1; then
  echo "error: ${CODEQL_TOOL_NAME} is required" >&2
  exit 1
fi

rm -rf "${DB_DIR}"
"${CODEQL_TOOL_NAME}" database create "${DB_DIR}" \
  --language="${CODEQL_LANGUAGE}" \
  --source-root "${REPO_ROOT}/${CODEQL_SOURCE_ROOT}" \
  --overwrite

"${CODEQL_TOOL_NAME}" database analyze "${DB_DIR}" \
  "${CODEQL_QUERY_SUITE}" \
  --download \
  --format=sarif-latest \
  --output "${RESULT_FILE}" \
  --threads=0
