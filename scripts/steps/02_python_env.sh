#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "${SCRIPT_DIR}/../lib/noise/python.sh"
source "${SCRIPT_DIR}/../lib/common/log.sh"
source "${SCRIPT_DIR}/../lib/deps/venv.sh"

log_info "[python] Verifying interpreter requirements for engine=${INFERENCE_ENGINE:-vllm}..."
ensure_python_runtime_for_engine "${INFERENCE_ENGINE:-vllm}"
log_info "[python] Interpreter ready"
