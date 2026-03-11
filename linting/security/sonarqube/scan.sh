#!/usr/bin/env bash
# run_sonarqube_scan - Run the SonarQube scanner against this repository.

set -euo pipefail

# shellcheck source=lib/constants.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/constants.sh"

cd "${REPO_ROOT}"

SCANNER_ARGS=(
  "-Dproject.settings=${SONAR_SETTINGS_PATH}"
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
  local docker_scanner_args=("${SCANNER_ARGS[@]}")

  if [[ ${scanner_url} == "${SONAR_LOCALHOST_URLS[0]}" || ${scanner_url} == "${SONAR_LOCALHOST_URLS[1]}" ]]; then
    scanner_url="$(printf '%s' "${scanner_url}" | sed 's#://127\.0\.0\.1:#://host.docker.internal:#; s#://localhost:#://host.docker.internal:#')"
    docker_args+=(--add-host "host.docker.internal:host-gateway")
  fi

  docker_scanner_args[0]="-Dproject.settings=/usr/src/${SONAR_SETTINGS_FILE}"

  docker "${docker_args[@]}" \
    "${SONAR_SCANNER_IMAGE}" \
    sonar-scanner \
    "-Dsonar.host.url=${scanner_url}" \
    "${docker_scanner_args[@]}"
}

if command -v sonar-scanner >/dev/null 2>&1; then
  run_sonar_local
  exit 0
fi

require_docker
run_sonar_docker
