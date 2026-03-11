#!/usr/bin/env bash

set -euo pipefail

# shellcheck source=bootstrap.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/bootstrap.sh"

# generate_sonarqube_inputs - Build coverage and test-report artifacts for SonarQube.
generate_sonarqube_inputs() {
  if [[ ${SONAR_SKIP_COVERAGE:-0} == "1" ]]; then
    echo "SonarQube coverage generation skipped (SONAR_SKIP_COVERAGE=1)"
    return 0
  fi

  "${REPO_ROOT}/scripts/coverage.sh"
}
