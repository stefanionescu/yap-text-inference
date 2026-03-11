#!/usr/bin/env bash
# scan_codeql - Create and analyze a local CodeQL database for Python sources.

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
if [[ ! -x ${CODEQL_COMMAND} ]]; then
  echo "error: missing executable ${CODEQL_COMMAND}" >&2
  exit 1
fi

rm -rf "${DB_DIR}"
mkdir -p "$(dirname "${RESULT_FILE}")"

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
  --format=sarif-latest
  --output "${RESULT_FILE}"
  --threads="${THREADS}"
  --no-print-diagnostics-summary
)

if [[ -n ${RAM_MB} ]]; then
  CREATE_ARGS+=(--ram="${RAM_MB}")
  ANALYZE_ARGS+=(--ram="${RAM_MB}")
fi

echo "=== codeql > ${CODEQL_TARGET_NAME} (${CODEQL_LANGUAGE}) ==="
"${CODEQL_COMMAND}" "${CREATE_ARGS[@]}"
"${CODEQL_COMMAND}" "${ANALYZE_ARGS[@]}"

echo "codeql sarif: ${RESULT_FILE}"
if [[ ${KEEP_DB} == "1" ]]; then
  echo "codeql db kept: ${DB_DIR}"
fi
