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

# resolve_codeql_command - Resolve the local, cached, or auto-installed CodeQL binary.
resolve_codeql_command() {
  local cached_binary="${REPO_ROOT}/${SECURITY_CACHE_RELATIVE_DIR}/bin/${CODEQL_TOOL_NAME}"

  if command -v "${CODEQL_TOOL_NAME}" >/dev/null 2>&1; then
    command -v "${CODEQL_TOOL_NAME}"
    return 0
  fi
  if [[ -x ${cached_binary} ]]; then
    echo "${cached_binary}"
    return 0
  fi

  bash "${REPO_ROOT}/linting/security/install.sh" "${CODEQL_TOOL_NAME}" >/dev/null
  if [[ -x ${cached_binary} ]]; then
    echo "${cached_binary}"
    return 0
  fi

  echo "error: unable to resolve ${CODEQL_TOOL_NAME}" >&2
  exit 1
}

CODEQL_COMMAND="$(resolve_codeql_command)"

rm -rf "${DB_DIR}"
"${CODEQL_COMMAND}" database create "${DB_DIR}" \
  --language="${CODEQL_LANGUAGE}" \
  --source-root "${REPO_ROOT}/${CODEQL_SOURCE_ROOT}" \
  --overwrite

"${CODEQL_COMMAND}" database analyze "${DB_DIR}" \
  "${CODEQL_QUERY_SUITE}" \
  --download \
  --format=sarif-latest \
  --output "${RESULT_FILE}" \
  --threads=0
