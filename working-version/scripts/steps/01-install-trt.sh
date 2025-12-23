#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# shellcheck disable=SC1091
source "${ROOT_DIR}/lib/common.sh"
load_env_if_present
load_environment

exec bash "${ROOT_DIR}/setup/install_dependencies.sh" "$@"
