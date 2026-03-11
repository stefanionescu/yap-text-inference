#!/usr/bin/env bash

set -euo pipefail

# shellcheck disable=SC2034 # lint:justify -- reason: sourced constants library exports shared SonarQube values for sibling scripts -- ticket: N/A
# shellcheck source=bootstrap.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/bootstrap.sh"

SONAR_URL="${SONAR_HOST_URL:-${SONAR_DEFAULT_HOST_URL}}"
SONAR_TOKEN="${SONAR_TOKEN:-}"
SONAR_LOGIN="${SONAR_LOGIN:-${SONAR_DEFAULT_LOGIN}}"
SONAR_PASSWORD="${SONAR_PASSWORD:-${SONAR_DEFAULT_PASSWORD}}"
# shellcheck disable=SC2034 # lint:justify -- reason: sourced by scan.sh to resolve the effective settings path -- ticket: N/A
SONAR_SETTINGS_PATH="$(resolve_sonar_repo_path "${SONAR_SETTINGS_FILE}")"
# shellcheck disable=SC2034 # lint:justify -- reason: sourced by collect.sh to print the effective dashboard URL -- ticket: N/A
SONAR_DASHBOARD_URL="${SONAR_URL}/dashboard?id=${SONAR_DASHBOARD_ID}"
