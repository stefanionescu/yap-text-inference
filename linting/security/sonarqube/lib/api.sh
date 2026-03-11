#!/usr/bin/env bash

set -euo pipefail

# shellcheck source=constants.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/constants.sh"

# sonar_api_get - Run an authenticated GET request against the SonarQube API.
sonar_api_get() {
  local endpoint="$1"
  if [[ -n ${SONAR_TOKEN} ]]; then
    curl -fsS -u "${SONAR_TOKEN}:" "${SONAR_URL}${endpoint}"
    return 0
  fi
  curl -fsS -u "${SONAR_LOGIN}:${SONAR_PASSWORD}" "${SONAR_URL}${endpoint}"
}

# wait_for_sonar_api - Wait until a SonarQube API endpoint responds successfully.
wait_for_sonar_api() {
  local endpoint="$1"
  local attempts="${2:-60}"
  local delay_s="${3:-5}"
  local remaining="${attempts}"

  while [[ ${remaining} -gt 0 ]]; do
    if sonar_api_get "${endpoint}" >/dev/null 2>&1; then
      return 0
    fi
    sleep "${delay_s}"
    remaining=$((remaining - 1))
  done

  echo "error: SonarQube API did not become ready for ${endpoint}" >&2
  exit 1
}
