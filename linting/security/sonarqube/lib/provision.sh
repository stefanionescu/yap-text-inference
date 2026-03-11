#!/usr/bin/env bash

set -euo pipefail

# shellcheck source=api.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/api.sh"

# ensure_sonarqube_bootstrap - Validate that the local SonarQube service is reachable before scanning.
ensure_sonarqube_bootstrap() {
  wait_for_sonar_api "/api/system/status"
}
