#!/usr/bin/env bash
# manage_sonarqube_server - Start, stop, or ensure a local SonarQube server container.

set -euo pipefail

# shellcheck source=lib/provision.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/provision.sh"

CONTAINER_NAME="${SONAR_SERVER_CONTAINER_NAME}"
IMAGE_NAME="${SONAR_SERVER_IMAGE}"
COMMAND="${1:-ensure}"

require_docker

case "${COMMAND}" in
  ensure | start)
    if ! docker ps --format '{{.Names}}' | grep -qx "${CONTAINER_NAME}"; then
      docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
      docker run -d \
        --name "${CONTAINER_NAME}" \
        -p "${SONAR_SERVER_PORT}:9000" \
        "${IMAGE_NAME}" >/dev/null
    fi
    ensure_sonarqube_bootstrap
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
