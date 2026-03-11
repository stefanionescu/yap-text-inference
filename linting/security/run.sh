#!/usr/bin/env bash
# run_security_checks - Run static analysis, dependency, secret, and container security scans.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/../.. && pwd)"
# shellcheck source=../common.sh
source "${ROOT_DIR}/linting/common.sh"
ensure_repo_python_env
RUN_SONAR="${RUN_SONAR:-0}"
ENABLE_TRIVY="${ENABLE_TRIVY:-1}"
SKIP_CODEQL="${SKIP_CODEQL:-0}"

# run_cmd - Run a command and show its buffered output on failure.
run_cmd() {
  local label="$1"
  shift
  local tmp
  tmp="$(mktemp)"
  echo "=== security > ${label} ==="
  if "$@" >"${tmp}" 2>&1; then
    rm -f "${tmp}"
    echo "[security] ${label} ok"
    return 0
  fi
  echo "[security] ${label} failed" >&2
  cat "${tmp}" >&2
  rm -f "${tmp}"
  return 1
}

cd "${ROOT_DIR}"
run_cmd "semgrep" bash linting/semgrep/run.sh
run_cmd "bandit" python -m bandit -c bandit.yaml -r src docker linting
run_cmd "pip-audit" bash linting/security/pip_audit/run.sh
run_cmd "licenses" python -m linting.licenses.audit
run_cmd "gitleaks" bash linting/security/gitleaks/run.sh
run_cmd "bearer" bash linting/security/bearer/run.sh
if [[ ${ENABLE_TRIVY} == "1" ]]; then
  run_cmd "trivy" bash linting/security/trivy/run.sh all
else
  echo "[security] trivy skipped (set ENABLE_TRIVY=1 to enable)"
fi
if [[ ${SKIP_CODEQL} != "1" ]]; then
  run_cmd "codeql" bash linting/security/codeql/run.sh
fi

if [[ ${RUN_SONAR} == "1" ]]; then
  run_cmd "sonarqube" bash linting/security/sonarqube/run.sh
fi
