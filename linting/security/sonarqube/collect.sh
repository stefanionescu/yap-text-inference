#!/usr/bin/env bash
# collect_sonarqube_results - Print the local SonarQube dashboard URL.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../common.sh
source "${SCRIPT_DIR}/../common.sh"
source_security_config "sonarqube"

echo "SonarQube dashboard: ${SONAR_HOST_URL:-${SONAR_DEFAULT_HOST_URL}}/dashboard?id=${SONAR_DASHBOARD_ID}"
