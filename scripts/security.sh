#!/usr/bin/env bash
# run_security_checks - Run static analysis, dependency, secret, and container security scans.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
RUN_SONAR="${RUN_SONAR:-0}"
SKIP_CODEQL="${SKIP_CODEQL:-0}"

# run_cmd - Run a command and show its buffered output on failure.
run_cmd() {
  local label="$1"
  shift
  local tmp
  tmp="$(mktemp)"
  if "$@" >"${tmp}" 2>&1; then
    rm -f "${tmp}"
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
run_cmd "osv-scanner" bash linting/security/osv/run.sh
run_cmd "gitleaks" bash linting/security/gitleaks/run.sh
run_cmd "bearer" bash linting/security/bearer/run.sh
run_cmd "trivy" bash linting/security/trivy/run.sh all
if [[ ${SKIP_CODEQL} != "1" ]]; then
  run_cmd "codeql" bash linting/security/codeql/run.sh
fi

if [[ ${RUN_SONAR} == "1" ]]; then
  run_cmd "sonarqube" bash linting/security/sonarqube/run.sh
fi
