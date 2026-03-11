#!/usr/bin/env bash
# run_sonarqube - Generate coverage, ensure SonarQube is running, scan, and print the dashboard URL.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

"${REPO_ROOT}/scripts/coverage.sh"
"${SCRIPT_DIR}/server.sh" ensure
"${SCRIPT_DIR}/scan.sh"
"${SCRIPT_DIR}/collect.sh"
