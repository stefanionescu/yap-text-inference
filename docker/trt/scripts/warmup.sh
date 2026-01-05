#!/usr/bin/env bash
# TRT warmup wrapper - delegates to the shared warmup script.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Find common scripts directory (works in Docker and dev contexts)
if [ -d "/app/common/scripts" ]; then
  COMMON_DIR="/app/common/scripts"
elif [ -d "${SCRIPT_DIR}/../../common/scripts" ]; then
  COMMON_DIR="${SCRIPT_DIR}/../../common/scripts"
else
  echo "[warmup] ERROR: Cannot find common scripts directory" >&2
  exit 1
fi

exec "${COMMON_DIR}/warmup.sh"
