#!/usr/bin/env bash
# collect_sonarqube_results - Print the local SonarQube dashboard URL and quality gate status.

set -euo pipefail

# shellcheck source=lib/gate.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/gate.sh"

echo "SonarQube dashboard: ${SONAR_DASHBOARD_URL}"
print_quality_gate_summary
