#!/usr/bin/env bash

set -euo pipefail

# shellcheck source=api.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/api.sh"

# read_quality_gate_status - Print the current project quality gate status when available.
read_quality_gate_status() {
  local response
  response="$(sonar_api_get "/api/qualitygates/project_status?projectKey=${SONAR_DASHBOARD_ID}" || true)"
  if [[ -z ${response} ]]; then
    return 1
  fi

  printf '%s' "${response}" | tr -d '\n' | sed -n 's/.*"projectStatus":{"status":"\([^"]*\)".*/\1/p'
}

# print_quality_gate_summary - Print the quality gate result for the configured project.
print_quality_gate_summary() {
  local status
  status="$(read_quality_gate_status || true)"
  if [[ -z ${status} ]]; then
    echo "SonarQube quality gate: unavailable"
    return 0
  fi

  echo "SonarQube quality gate: ${status}"
  if [[ ${status} != "OK" ]]; then
    echo "Review the SonarQube dashboard for failing conditions."
  fi
}
