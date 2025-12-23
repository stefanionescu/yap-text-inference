#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# shellcheck disable=SC1091
source "${ROOT_DIR}/lib/common.sh"
load_env_if_present
load_environment

echo "[bootstrap] Validating CUDA toolkit/driver (need CUDA 13.x support)..."
if ! assert_cuda13_driver "bootstrap"; then
  echo "[bootstrap] CUDA validation failed; aborting." >&2
  exit 1
fi

exec bash "${ROOT_DIR}/setup/bootstrap.sh" "$@"
