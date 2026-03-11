#!/usr/bin/env bash

set -euo pipefail

# shellcheck source=api.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/api.sh"

# require_sonarqube_provision_dependencies - Abort if jq is unavailable for JSON parsing.
require_sonarqube_provision_dependencies() {
  if ! command -v jq >/dev/null 2>&1; then
    echo "error: jq is required for SonarQube provisioning" >&2
    exit 1
  fi
}

# sonar_urlencode - URL-encode a string value for SonarQube search endpoints.
sonar_urlencode() {
  printf '%s' "$1" | jq -sRr @uri
}

# generate_sonarqube_secret - Generate a repo-local random secret.
generate_sonarqube_secret() {
  python - <<'PY'
import secrets

print(f"Yap_Text-Inference_{secrets.token_hex(12)}!1A")
PY
}

# resolve_target_admin_password - Return the desired persisted SonarQube admin password.
resolve_target_admin_password() {
  local stored_password

  stored_password="$(read_secret_file "${SONAR_ADMIN_PASSWORD_PATH}" 2>/dev/null || true)"
  if [[ -n ${stored_password} && ${stored_password} != "${SONAR_DEFAULT_PASSWORD}" ]]; then
    printf '%s\n' "${stored_password}"
    return 0
  fi

  generate_sonarqube_secret
}

# stored_token_is_valid - Return success when the persisted analysis token is accepted by SonarQube.
stored_token_is_valid() {
  local token
  token="$(read_secret_file "${SONAR_TOKEN_PATH}" 2>/dev/null || true)"
  [[ -n ${token} ]] || return 1

  local response
  response="$(sonar_token_validation_response "${token}" 2>/dev/null || true)"
  grep -q '"valid":true' <<<"${response}"
}

# admin_credentials_are_valid - Return success when the current admin login/password can access admin APIs.
admin_credentials_are_valid() {
  local status_code

  status_code="$(sonar_admin_api_status GET "/api/user_tokens/search" || true)"
  [[ ${status_code} == "200" ]]
}

# change_admin_password - Ensure SonarQube uses the repo-local generated admin password.
change_admin_password() {
  local target_password
  local status_code

  target_password="$(resolve_target_admin_password)"

  if admin_credentials_are_valid; then
    if [[ ${SONAR_PASSWORD} == "${target_password}" ]]; then
      write_secret_file "${SONAR_ADMIN_PASSWORD_PATH}" "${target_password}"
      return 0
    fi

    if [[ ${SONAR_PASSWORD} != "${SONAR_DEFAULT_PASSWORD}" ]]; then
      write_secret_file "${SONAR_ADMIN_PASSWORD_PATH}" "${SONAR_PASSWORD}"
      return 0
    fi
  fi

  status_code="$(sonar_default_admin_api_status POST "/api/users/change_password" \
    --data-urlencode "login=${SONAR_DEFAULT_LOGIN}" \
    --data-urlencode "previousPassword=${SONAR_DEFAULT_PASSWORD}" \
    --data-urlencode "password=${target_password}" || true)"
  if [[ ${status_code} == "200" || ${status_code} == "204" ]]; then
    write_secret_file "${SONAR_ADMIN_PASSWORD_PATH}" "${target_password}"
    SONAR_PASSWORD="${target_password}"
    return 0
  fi

  echo "error: failed to provision SonarQube admin credentials; reset the local server and retry" >&2
  exit 1
}

# provision_token - Generate and persist the repo-local SonarQube analysis token.
provision_token() {
  if stored_token_is_valid; then
    SONAR_TOKEN="$(read_secret_file "${SONAR_TOKEN_PATH}")"
    return 0
  fi

  rm -f "${SONAR_TOKEN_PATH}"
  sonar_admin_api_request POST "/api/user_tokens/revoke" --data-urlencode "name=${SONAR_TOKEN_NAME}" >/dev/null || true

  local response
  local token

  response="$(sonar_admin_api_request POST "/api/user_tokens/generate" \
    --data-urlencode "name=${SONAR_TOKEN_NAME}" \
    --data-urlencode "type=GLOBAL_ANALYSIS_TOKEN")"
  token="$(jq -r '.token // empty' <<<"${response}")"
  if [[ -z ${token} ]]; then
    echo "error: failed to provision SonarQube analysis token" >&2
    exit 1
  fi

  write_secret_file "${SONAR_TOKEN_PATH}" "${token}"
  # shellcheck disable=SC2034 # lint:justify -- reason: sourced provisioning helpers refresh the in-memory token for later sibling calls -- ticket: N/A
  SONAR_TOKEN="${token}"
}

# quality_gate_exists - Return success when the configured quality gate exists.
quality_gate_exists() {
  local response
  response="$(sonar_admin_api_json "/api/qualitygates/list")"
  jq -e --arg gate_name "${SONAR_QUALITY_GATE_NAME}" '.qualitygates[]? | select(.name == $gate_name)' <<<"${response}" >/dev/null
}

# provision_quality_gate - Create or update the strict SonarQube quality gate for this repo.
provision_quality_gate() {
  local response
  local condition_id
  local metric
  local op
  local threshold
  local condition
  local encoded_gate_name

  if ! quality_gate_exists; then
    sonar_admin_api_status POST "/api/qualitygates/create" --data-urlencode "name=${SONAR_QUALITY_GATE_NAME}" >/dev/null
  fi

  encoded_gate_name="$(sonar_urlencode "${SONAR_QUALITY_GATE_NAME}")"
  response="$(sonar_admin_api_json "/api/qualitygates/show?name=${encoded_gate_name}")"
  while IFS= read -r condition_id; do
    [[ -n ${condition_id} ]] || continue
    sonar_admin_api_status POST "/api/qualitygates/delete_condition" --data-urlencode "id=${condition_id}" >/dev/null
  done < <(jq -r '.conditions[]?.id // empty' <<<"${response}")

  for condition in "${SONAR_GATE_CONDITIONS[@]}"; do
    IFS=':' read -r metric op threshold <<<"${condition}"
    sonar_admin_api_status POST "/api/qualitygates/create_condition" \
      --data-urlencode "gateName=${SONAR_QUALITY_GATE_NAME}" \
      --data-urlencode "metric=${metric}" \
      --data-urlencode "op=${op}" \
      --data-urlencode "error=${threshold}" >/dev/null
  done

  sonar_admin_api_status POST "/api/qualitygates/set_as_default" \
    --data-urlencode "name=${SONAR_QUALITY_GATE_NAME}" >/dev/null
}

# resolve_profile_key - Return the configured quality profile key for a Sonar language.
resolve_profile_key() {
  local language="$1"
  local encoded_profile_name
  local response

  encoded_profile_name="$(sonar_urlencode "${SONAR_QUALITY_PROFILE_NAME}")"
  response="$(sonar_admin_api_json "/api/qualityprofiles/search?language=${language}&qualityProfile=${encoded_profile_name}")"
  jq -r '.profiles[]?.key // empty' <<<"${response}" | head -n 1
}

# resolve_profile_source_key - Return the built-in source profile key used to seed a custom profile.
resolve_profile_source_key() {
  local language="$1"
  local response
  local source_key

  response="$(sonar_admin_api_json "/api/qualityprofiles/search?language=${language}&qualityProfile=Sonar%20way")"
  source_key="$(jq -r '.profiles[]?.key // empty' <<<"${response}" | head -n 1)"
  if [[ -n ${source_key} ]]; then
    echo "${source_key}"
    return 0
  fi

  response="$(sonar_admin_api_json "/api/qualityprofiles/search?language=${language}&defaults=true")"
  jq -r '.profiles[]?.key // empty' <<<"${response}" | head -n 1
}

# provision_quality_profiles - Create the repo-local strict quality profiles and set them as defaults.
provision_quality_profiles() {
  local language
  local response
  local rule_count
  local profile_key
  local source_key

  for language in "${SONAR_PROFILE_LANGUAGES[@]}"; do
    response="$(sonar_admin_api_json "/api/rules/search?languages=${language}&ps=1")"
    rule_count="$(jq -r '.total // 0' <<<"${response}")"
    if [[ ${rule_count} == "0" ]]; then
      continue
    fi

    profile_key="$(resolve_profile_key "${language}")"
    if [[ -z ${profile_key} ]]; then
      source_key="$(resolve_profile_source_key "${language}")"
      if [[ -z ${source_key} ]]; then
        echo "error: failed to resolve a source quality profile for Sonar language ${language}" >&2
        exit 1
      fi
      sonar_admin_api_status POST "/api/qualityprofiles/copy" \
        --data-urlencode "fromKey=${source_key}" \
        --data-urlencode "toName=${SONAR_QUALITY_PROFILE_NAME}" >/dev/null
      profile_key="$(resolve_profile_key "${language}")"
    fi

    if [[ -z ${profile_key} ]]; then
      echo "error: failed to resolve SonarQube quality profile key for ${language}" >&2
      exit 1
    fi

    sonar_admin_api_status POST "/api/qualityprofiles/activate_rules" \
      --data-urlencode "targetKey=${profile_key}" \
      --data-urlencode "languages=${language}" >/dev/null
    sonar_admin_api_status POST "/api/qualityprofiles/set_default" \
      --data-urlencode "qualityProfile=${SONAR_QUALITY_PROFILE_NAME}" \
      --data-urlencode "language=${language}" >/dev/null
  done
}

# sonarqube_project_exists - Return success when the configured project key is present on the server.
sonarqube_project_exists() {
  local response
  local encoded_project_key

  encoded_project_key="$(sonar_urlencode "${SONAR_DASHBOARD_ID}")"
  response="$(sonar_admin_api_json "/api/projects/search?projects=${encoded_project_key}")"
  jq -e '.components | length > 0' <<<"${response}" >/dev/null
}

# sync_sonarqube_project_policy - Re-apply the repo gate/profile to the provisioned project.
sync_sonarqube_project_policy() {
  local language

  require_sonarqube_provision_dependencies
  if ! sonarqube_project_exists; then
    return 0
  fi

  sonar_admin_api_status POST "/api/qualitygates/select" \
    --data-urlencode "projectKey=${SONAR_DASHBOARD_ID}" \
    --data-urlencode "gateName=${SONAR_QUALITY_GATE_NAME}" >/dev/null

  for language in "${SONAR_PROFILE_LANGUAGES[@]}"; do
    sonar_admin_api_status POST "/api/qualityprofiles/add_project" \
      --data-urlencode "project=${SONAR_DASHBOARD_ID}" \
      --data-urlencode "language=${language}" \
      --data-urlencode "qualityProfile=${SONAR_QUALITY_PROFILE_NAME}" >/dev/null || true
  done
}

# ensure_sonarqube_bootstrap - Provision local credentials, token, and strict quality policy before scanning.
ensure_sonarqube_bootstrap() {
  wait_for_sonar_api "/api/system/status"
  require_sonarqube_provision_dependencies
  change_admin_password
  provision_token
  provision_quality_gate
  provision_quality_profiles
}
