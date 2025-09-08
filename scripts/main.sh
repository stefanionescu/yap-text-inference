#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

source "${SCRIPT_DIR}/utils.sh"

log_info "Starting RunPod setup orchestrator"

"${SCRIPT_DIR}/01_check_gpu.sh"
"${SCRIPT_DIR}/02_python_env.sh"
"${SCRIPT_DIR}/03_install_deps.sh"
"${SCRIPT_DIR}/04_prepare_lmcache.sh"
"${SCRIPT_DIR}/05_env_defaults.sh"
"${SCRIPT_DIR}/06_start_server.sh"


