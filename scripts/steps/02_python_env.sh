#!/usr/bin/env bash
# =============================================================================
# Python Environment Verification
# =============================================================================
# Verifies that the correct Python interpreter is available for the selected
# inference engine. TRT-LLM requires Python 3.10; vLLM supports 3.10-3.12.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "${SCRIPT_DIR}/../lib/noise/python.sh"
source "${SCRIPT_DIR}/../lib/common/log.sh"
source "${SCRIPT_DIR}/../lib/deps/venv.sh"

log_info "[python] Verifying interpreter requirements for engine=${INFERENCE_ENGINE:-vllm}..."
ensure_python_runtime_for_engine "${INFERENCE_ENGINE:-vllm}"
log_info "[python] Interpreter ready"
