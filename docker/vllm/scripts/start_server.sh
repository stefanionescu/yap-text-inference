#!/usr/bin/env bash
# shellcheck disable=SC1091
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/logs.sh"
source "/app/common/scripts/server.sh"

cd /app
ROOT_DIR="${ROOT_DIR:-/app}"

start_server_with_warmup "vllm" "${SCRIPT_DIR}/warmup.sh" "${ROOT_DIR}"
