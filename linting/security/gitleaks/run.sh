#!/usr/bin/env bash
# run_gitleaks - Run Gitleaks against the repository filesystem.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../common.sh
source "${SCRIPT_DIR}/../common.sh"
source_security_config "gitleaks"

cd "${REPO_ROOT}"

if command -v gitleaks >/dev/null 2>&1; then
  gitleaks detect --no-git --source . --config "${GITLEAKS_CONFIG_FILE}"
  exit 0
fi

require_docker
docker run --rm \
  -v "${REPO_ROOT}:/path" \
  "${GITLEAKS_IMAGE}" \
  detect --no-git --source /path --config "/path/${GITLEAKS_CONFIG_FILE}"
