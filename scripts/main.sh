#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

source "${SCRIPT_DIR}/utils.sh"

log_info "Starting RunPod setup orchestrator"

bash "${SCRIPT_DIR}/01_check_gpu.sh"
bash "${SCRIPT_DIR}/02_python_env.sh"
bash "${SCRIPT_DIR}/03_install_deps.sh"
bash "${SCRIPT_DIR}/04_prepare_lmcache.sh"
bash "${SCRIPT_DIR}/05_env_defaults.sh"
bash "${SCRIPT_DIR}/06_start_server.sh"
bash "${SCRIPT_DIR}/07_follow_logs.sh"


