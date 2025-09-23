#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

source "${SCRIPT_DIR}/utils.sh"

log_info "Starting RunPod setup orchestrator"

# Parse simple flags (e.g., 4-bit)
FORCE_4BIT=0
for arg in "$@"; do
  case "$arg" in
    4-bit|--4-bit|--4bit|4bit|--quant=4-bit|--quant=4bit)
      FORCE_4BIT=1
      ;;
  esac
done
if [ "${FORCE_4BIT}" -eq 1 ]; then
  export FORCE_4BIT=1
  log_info "4-bit mode enabled (GPTQ)"
fi

bash "${SCRIPT_DIR}/01_check_gpu.sh"
bash "${SCRIPT_DIR}/02_python_env.sh"
bash "${SCRIPT_DIR}/03_install_deps.sh"
bash "${SCRIPT_DIR}/04_env_defaults.sh"
bash "${SCRIPT_DIR}/05_start_server.sh"
bash "${SCRIPT_DIR}/06_follow_logs.sh"


