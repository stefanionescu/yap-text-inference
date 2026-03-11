#!/usr/bin/env bash
# run_gitleaks - Run Gitleaks against the repository filesystem.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../common.sh
source "${SCRIPT_DIR}/../common.sh"
source_security_config "gitleaks"

cd "${REPO_ROOT}"

GITLEAKS_MODE="${1:-scan}"

# resolve_gitleaks_command - Resolve the local, cached, or auto-installed Gitleaks binary.
resolve_gitleaks_command() {
  local cached_binary="${REPO_ROOT}/${SECURITY_CACHE_RELATIVE_DIR}/bin/${GITLEAKS_TOOL_NAME}"

  if command -v "${GITLEAKS_TOOL_NAME}" >/dev/null 2>&1; then
    command -v "${GITLEAKS_TOOL_NAME}"
    return 0
  fi
  if [[ -x ${cached_binary} ]]; then
    echo "${cached_binary}"
    return 0
  fi
  if bash "${REPO_ROOT}/linting/security/install.sh" "${GITLEAKS_TOOL_NAME}" >/dev/null 2>&1 && [[ -x ${cached_binary} ]]; then
    echo "${cached_binary}"
    return 0
  fi
  return 1
}

# run_gitleaks_scan - Run the standard baseline-backed gitleaks detection flow.
run_gitleaks_scan() {
  local runner="$1"
  "${runner}" detect \
    --no-git \
    --source . \
    --config "${GITLEAKS_CONFIG_FILE}" \
    --baseline-path "${GITLEAKS_BASELINE_FILE}"
}

# generate_gitleaks_baseline - Regenerate the baseline JSON from current findings.
generate_gitleaks_baseline() {
  local runner="$1"
  rm -f "${GITLEAKS_BASELINE_FILE}"
  set +e
  "${runner}" detect \
    --no-git \
    --source . \
    --config "${GITLEAKS_CONFIG_FILE}" \
    --report-format json \
    --report-path "${GITLEAKS_BASELINE_FILE}"
  local status=$?
  set -e
  if [[ ! -f ${GITLEAKS_BASELINE_FILE} ]]; then
    echo "error: failed to generate ${GITLEAKS_BASELINE_FILE}" >&2
    exit 1
  fi
  if [[ ${status} -ne 0 && ${status} -ne 1 ]]; then
    exit "${status}"
  fi
}

if GITLEAKS_COMMAND="$(resolve_gitleaks_command)"; then
  case "${GITLEAKS_MODE}" in
    scan)
      run_gitleaks_scan "${GITLEAKS_COMMAND}"
      ;;
    baseline)
      generate_gitleaks_baseline "${GITLEAKS_COMMAND}"
      ;;
    *)
      echo "usage: $0 [scan|baseline]" >&2
      exit 1
      ;;
  esac
  exit 0
fi

require_docker
case "${GITLEAKS_MODE}" in
  scan)
    docker run --rm \
      -v "${REPO_ROOT}:/path" \
      "${GITLEAKS_IMAGE}" \
      detect --no-git --source /path --config "/path/${GITLEAKS_CONFIG_FILE}" --baseline-path "/path/${GITLEAKS_BASELINE_FILE}"
    ;;
  baseline)
    rm -f "${GITLEAKS_BASELINE_FILE}"
    set +e
    docker run --rm \
      -v "${REPO_ROOT}:/path" \
      "${GITLEAKS_IMAGE}" \
      detect --no-git --source /path --config "/path/${GITLEAKS_CONFIG_FILE}" --report-format json --report-path "/path/${GITLEAKS_BASELINE_FILE}"
    status=$?
    set -e
    if [[ ! -f ${GITLEAKS_BASELINE_FILE} ]]; then
      echo "error: failed to generate ${GITLEAKS_BASELINE_FILE}" >&2
      exit 1
    fi
    if [[ ${status} -ne 0 && ${status} -ne 1 ]]; then
      exit "${status}"
    fi
    ;;
  *)
    echo "usage: $0 [scan|baseline]" >&2
    exit 1
    ;;
esac
