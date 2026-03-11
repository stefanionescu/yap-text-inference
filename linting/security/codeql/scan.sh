#!/usr/bin/env bash
# scan_codeql - Create and analyze a local CodeQL database for Python sources.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
RUN_CODEQL_SCRIPT="${SCRIPT_DIR}/bin.sh"
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

SOURCE_ROOT="$(resolve_repo_path "${CODEQL_SOURCE_ROOT}")"
CONFIG_FILE="$(resolve_repo_path "${CODEQL_CONFIG_FILE}")"
DB_DIR="$(resolve_repo_path "${CODEQL_DATABASE_DIR}")"
RESULT_FILE="$(resolve_repo_path "${CODEQL_OUTPUT_FILE:-${CODEQL_RESULT_FILE}}")"
THREADS="${CODEQL_THREADS:-0}"
RAM_MB="${CODEQL_RAM_MB:-}"
KEEP_DB="${CODEQL_KEEP_DB:-0}"

if [[ ! -d ${SOURCE_ROOT} ]]; then
  echo "error: codeql source root not found: ${SOURCE_ROOT}" >&2
  exit 1
fi
if [[ ! -f ${CONFIG_FILE} ]]; then
  echo "error: codeql config not found: ${CONFIG_FILE}" >&2
  exit 1
fi
if [[ ! -x ${RUN_CODEQL_SCRIPT} ]]; then
  echo "error: missing executable ${RUN_CODEQL_SCRIPT}" >&2
  exit 1
fi

rm -rf "${DB_DIR}"
mkdir -p "$(dirname "${RESULT_FILE}")" "$(dirname "${DB_DIR}")"

# cleanup - Remove the temporary CodeQL database unless keep-db is enabled.
cleanup() {
  [[ ${KEEP_DB} == "1" ]] || rm -rf "${DB_DIR}"
}
trap cleanup EXIT

CREATE_ARGS=(
  database create "${DB_DIR}"
  --language="${CODEQL_LANGUAGE}"
  --source-root "${SOURCE_ROOT}"
  --codescanning-config="${CONFIG_FILE}"
  --threads="${THREADS}"
  --build-mode=none
  --overwrite
)
ANALYZE_ARGS=(
  database analyze "${DB_DIR}"
  "${CODEQL_QUERY_SUITE}"
  --download
  --format=sarifv2.1.0
  --output "${RESULT_FILE}"
  --threads="${THREADS}"
  --no-print-diagnostics-summary
)

if [[ -n ${RAM_MB} ]]; then
  CREATE_ARGS+=(--ram="${RAM_MB}")
  ANALYZE_ARGS+=(--ram="${RAM_MB}")
fi

echo "=== codeql > ${CODEQL_TARGET_NAME} (${CODEQL_LANGUAGE}) ==="
"${RUN_CODEQL_SCRIPT}" "${CREATE_ARGS[@]}"
"${RUN_CODEQL_SCRIPT}" "${ANALYZE_ARGS[@]}"

echo "codeql sarif: ${RESULT_FILE}"
if [[ ${KEEP_DB} == "1" ]]; then
  echo "codeql db kept: ${DB_DIR}"
fi
