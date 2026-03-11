#!/usr/bin/env bash

set -euo pipefail

# shellcheck disable=SC2034 # lint:justify -- reason: sourced constants library exports shared SonarQube values for sibling scripts -- ticket: N/A
# shellcheck source=bootstrap.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/bootstrap.sh"

SONAR_URL="$(sonar_base_url)"
if [[ -z ${SONAR_TOKEN:-} ]]; then
  SONAR_TOKEN="$(read_secret_file "$(sonar_token_path)" 2>/dev/null || true)"
fi
SONAR_LOGIN="${SONAR_LOGIN:-${SONAR_DEFAULT_LOGIN}}"
if [[ -z ${SONAR_PASSWORD:-} ]]; then
  SONAR_PASSWORD="$(read_secret_file "$(sonar_admin_password_path)" 2>/dev/null || true)"
  SONAR_PASSWORD="${SONAR_PASSWORD:-${SONAR_DEFAULT_PASSWORD}}"
fi
# shellcheck disable=SC2034 # lint:justify -- reason: sourced by provisioning helpers to reuse the resolved on-disk secret locations -- ticket: N/A
SONAR_ADMIN_PASSWORD_PATH="$(sonar_admin_password_path)"
# shellcheck disable=SC2034 # lint:justify -- reason: sourced by provisioning helpers to reuse the resolved on-disk secret locations -- ticket: N/A
SONAR_TOKEN_PATH="$(sonar_token_path)"
# shellcheck disable=SC2034 # lint:justify -- reason: sourced by report helpers to write generated Sonar markdown artifacts into the repo-local cache -- ticket: N/A
SONAR_ARTIFACT_DIR="$(sonar_artifact_dir)"
# shellcheck disable=SC2034 # lint:justify -- reason: sourced by scan.sh to resolve the effective settings path -- ticket: N/A
SONAR_SETTINGS_PATH="$(resolve_sonar_repo_path "${SONAR_SETTINGS_FILE}")"
# shellcheck disable=SC2034 # lint:justify -- reason: sourced by collect.sh to print the effective dashboard URL -- ticket: N/A
SONAR_DASHBOARD_URL="${SONAR_URL}/dashboard?id=${SONAR_DASHBOARD_ID}"
