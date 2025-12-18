#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../lib/common/log.sh"

log_info "[venv] Ensuring Python and pip are available"
python3 --version || python --version || true
python3 -m pip --version || python -m pip --version || true


