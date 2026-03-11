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
