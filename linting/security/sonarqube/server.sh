#!/usr/bin/env bash
# manage_sonarqube_server - Start, stop, or ensure a local SonarQube server container.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../common.sh
source "${SCRIPT_DIR}/../common.sh"
source_security_config "sonarqube"

CONTAINER_NAME="${SONAR_SERVER_CONTAINER_NAME}"
IMAGE_NAME="${SONAR_SERVER_IMAGE}"
SONAR_URL="${SONAR_HOST_URL:-${SONAR_DEFAULT_HOST_URL}}"
COMMAND="${1:-ensure}"

# wait_for_sonarqube - Wait until the SonarQube API responds successfully.
wait_for_sonarqube() {
  local attempts=60
  for _ in $(seq 1 "${attempts}"); do
    if curl -fsS "${SONAR_URL}/api/system/status" >/dev/null 2>&1; then
      return 0
    fi
    sleep 5
  done
  echo "error: SonarQube did not become ready" >&2
  exit 1
}

require_docker

case "${COMMAND}" in
  ensure | start)
    if ! docker ps --format '{{.Names}}' | grep -qx "${CONTAINER_NAME}"; then
      docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
      docker run -d \
        --name "${CONTAINER_NAME}" \
        -p 9000:9000 \
        "${IMAGE_NAME}" >/dev/null
    fi
    wait_for_sonarqube
    ;;
  stop)
    docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
    ;;
  status)
    docker ps --format '{{.Names}}' | grep -qx "${CONTAINER_NAME}"
    ;;
  *)
    echo "usage: $0 [ensure|start|stop|status]" >&2
    exit 1
    ;;
esac
