#!/usr/bin/env bash

set -euo pipefail

# shellcheck source=constants.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/constants.sh"

# sonar_api_auth - Print the effective scanner auth credential.
sonar_api_auth() {
  if [[ -n ${SONAR_TOKEN} ]]; then
    printf '%s:' "${SONAR_TOKEN}"
    return 0
  fi
  printf '%s:%s' "${SONAR_LOGIN}" "${SONAR_PASSWORD}"
}

# sonar_api_get - Run an authenticated GET request against the SonarQube API.
sonar_api_get() {
  local endpoint="$1"
  curl -fsS -u "$(sonar_api_auth)" "${SONAR_URL}${endpoint}"
}

# sonar_api_get_with_code - Run an authenticated GET request and append the HTTP status code.
sonar_api_get_with_code() {
  local endpoint="$1"
  curl -sS -u "$(sonar_api_auth)" -w "\n%{http_code}" "${SONAR_URL}${endpoint}"
}

# sonar_token_validation_response - Validate an explicit SonarQube token and return the JSON response body.
sonar_token_validation_response() {
  local token="$1"
  curl -fsS -u "${token}:" "${SONAR_URL}/api/authentication/validate"
}

# sonar_admin_api_status - Send an authenticated admin API request and return the HTTP status code.
sonar_admin_api_status() {
  local method="$1"
  local endpoint="$2"
  shift 2
  curl -sS -o /dev/null -w '%{http_code}' \
    -u "${SONAR_LOGIN}:${SONAR_PASSWORD}" \
    -X "${method}" \
    "${SONAR_URL}${endpoint}" \
    "$@"
}

# sonar_admin_api_json - Send an authenticated admin GET request and return the JSON response body.
sonar_admin_api_json() {
  local endpoint="$1"
  shift
  curl -fsS \
    -u "${SONAR_LOGIN}:${SONAR_PASSWORD}" \
    "${SONAR_URL}${endpoint}" \
    "$@"
}

# sonar_admin_api_request - Send an authenticated admin API request and return the response body.
sonar_admin_api_request() {
  local method="$1"
  local endpoint="$2"
  shift 2
  curl -fsS \
    -u "${SONAR_LOGIN}:${SONAR_PASSWORD}" \
    -X "${method}" \
    "${SONAR_URL}${endpoint}" \
    "$@"
}

# sonar_default_admin_api_status - Send a default-admin API request and return the HTTP status code.
sonar_default_admin_api_status() {
  local method="$1"
  local endpoint="$2"
  shift 2
  curl -sS -o /dev/null -w '%{http_code}' \
    -u "${SONAR_DEFAULT_LOGIN}:${SONAR_DEFAULT_PASSWORD}" \
    -X "${method}" \
    "${SONAR_URL}${endpoint}" \
    "$@"
}

# wait_for_sonar_api - Wait until a SonarQube API endpoint responds successfully.
wait_for_sonar_api() {
  local endpoint="$1"
  local attempts="${2:-60}"
  local delay_s="${3:-5}"
  local remaining="${attempts}"
  local response

  while [[ ${remaining} -gt 0 ]]; do
    response="$(curl -fsS "${SONAR_URL}${endpoint}" 2>/dev/null || sonar_api_get "${endpoint}" 2>/dev/null || true)"
    if [[ -n ${response} ]]; then
      if [[ ${endpoint} == "/api/system/status" ]]; then
        if grep -q '"status":"UP"' <<<"${response}"; then
          return 0
        fi
      else
        return 0
      fi
    fi
    sleep "${delay_s}"
    remaining=$((remaining - 1))
  done

  echo "error: SonarQube API did not become ready for ${endpoint}" >&2
  exit 1
}
