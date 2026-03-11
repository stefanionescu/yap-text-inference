#!/usr/bin/env bash
# run_sonarqube - Generate coverage, ensure SonarQube is running, scan, and print the dashboard URL.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=lib/coverage.sh
source "${SCRIPT_DIR}/lib/coverage.sh"

generate_sonarqube_inputs
"${SCRIPT_DIR}/server.sh" ensure
"${SCRIPT_DIR}/scan.sh"
# shellcheck source=lib/provision.sh
source "${SCRIPT_DIR}/lib/provision.sh"
sync_sonarqube_project_policy
"${SCRIPT_DIR}/collect.sh"
