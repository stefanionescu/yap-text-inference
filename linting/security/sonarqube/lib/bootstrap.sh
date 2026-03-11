#!/usr/bin/env bash

set -euo pipefail

SONAR_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SONAR_LIB_DIR}/../../../.." && pwd)"

# shellcheck source=../../common.sh
source "${SONAR_LIB_DIR}/../../common.sh"
source_security_config "sonarqube"

# resolve_sonar_repo_path - Resolve a repo-relative path while preserving absolute inputs.
resolve_sonar_repo_path() {
  local value="$1"
  if [[ ${value} == /* ]]; then
    echo "${value}"
    return 0
  fi
  echo "${REPO_ROOT}/${value}"
}

# sonar_base_url - Resolve the effective SonarQube base URL.
sonar_base_url() {
  echo "${SONAR_HOST_URL:-${SONAR_DEFAULT_HOST_URL}}"
}

# sonar_admin_password_path - Resolve the repo-local SonarQube admin password file path.
sonar_admin_password_path() {
  resolve_sonar_repo_path "${SONAR_ADMIN_PASSWORD_FILE}"
}

# sonar_token_path - Resolve the repo-local SonarQube analysis token file path.
sonar_token_path() {
  resolve_sonar_repo_path "${SONAR_TOKEN_FILE}"
}

# sonar_artifact_dir - Resolve the repo-local SonarQube artifact directory.
sonar_artifact_dir() {
  dirname "$(sonar_token_path)"
}

# read_secret_file - Print a file's single-line secret value when it exists.
read_secret_file() {
  local path="$1"
  [[ -f ${path} ]] || return 1
  tr -d '\r\n' <"${path}"
}

# write_secret_file - Persist a secret to disk with restrictive permissions.
write_secret_file() {
  local path="$1"
  local value="$2"
  mkdir -p "$(dirname "${path}")"
  printf '%s' "${value}" >"${path}"
  chmod 600 "${path}"
}
