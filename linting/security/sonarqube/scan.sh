#!/usr/bin/env bash
# run_sonarqube_scan - Run the SonarQube scanner against this repository.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../common.sh
source "${SCRIPT_DIR}/../common.sh"
source_security_config "sonarqube"

SONAR_URL="${SONAR_HOST_URL:-${SONAR_DEFAULT_HOST_URL}}"
SONAR_TOKEN="${SONAR_TOKEN:-}"
SONAR_LOGIN="${SONAR_LOGIN:-${SONAR_DEFAULT_LOGIN}}"
SONAR_PASSWORD="${SONAR_PASSWORD:-${SONAR_DEFAULT_PASSWORD}}"

cd "${REPO_ROOT}"

SCANNER_ARGS=(
  "-Dproject.settings=${SONAR_SETTINGS_FILE}"
  "-Dsonar.qualitygate.wait=${SONAR_QUALITYGATE_WAIT}"
  "-Dsonar.qualitygate.timeout=${SONAR_QUALITYGATE_TIMEOUT}"
)

if [[ -n ${SONAR_TOKEN} ]]; then
  SCANNER_ARGS+=("-Dsonar.token=${SONAR_TOKEN}")
else
  SCANNER_ARGS+=("-Dsonar.login=${SONAR_LOGIN}")
  SCANNER_ARGS+=("-Dsonar.password=${SONAR_PASSWORD}")
fi

# run_sonar_local - Run the Sonar scanner CLI from the local machine.
run_sonar_local() {
  sonar-scanner "-Dsonar.host.url=${SONAR_URL}" "${SCANNER_ARGS[@]}"
}

# run_sonar_docker - Run the official Sonar scanner inside Docker.
run_sonar_docker() {
  local scanner_url="${SONAR_URL}"
  local docker_args=(run --rm -v "${REPO_ROOT}:/usr/src" -w /usr/src)

  if [[ ${scanner_url} == "${SONAR_LOCALHOST_URLS[0]}" || ${scanner_url} == "${SONAR_LOCALHOST_URLS[1]}" ]]; then
    scanner_url="http://host.docker.internal:9000"
    docker_args+=(--add-host "host.docker.internal:host-gateway")
  fi

  docker "${docker_args[@]}" \
    "${SONAR_SCANNER_IMAGE}" \
    sonar-scanner \
    "-Dsonar.host.url=${scanner_url}" \
    "${SCANNER_ARGS[@]}"
}

if command -v sonar-scanner >/dev/null 2>&1; then
  run_sonar_local
  exit 0
fi

require_docker
run_sonar_docker
