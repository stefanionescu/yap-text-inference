#!/usr/bin/env bash
# shellcheck disable=SC1091
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/logs.sh"

cd /app
ROOT_DIR="${ROOT_DIR:-/app}"

# Resolve uvicorn command
if command -v uvicorn >/dev/null 2>&1; then
  UVICORN_CMD=(uvicorn src.server:app --host 0.0.0.0 --port 8000 --workers 1)
elif command -v python >/dev/null 2>&1 && PYTHONPATH="${ROOT_DIR}${PYTHONPATH:+:${PYTHONPATH}}" python -m src.scripts.validation.package uvicorn >/dev/null 2>&1; then
  UVICORN_CMD=(python -m uvicorn src.server:app --host 0.0.0.0 --port 8000 --workers 1)
elif command -v python3 >/dev/null 2>&1 && PYTHONPATH="${ROOT_DIR}${PYTHONPATH:+:${PYTHONPATH}}" python3 -m src.scripts.validation.package uvicorn >/dev/null 2>&1; then
  UVICORN_CMD=(python3 -m uvicorn src.server:app --host 0.0.0.0 --port 8000 --workers 1)
else
  echo "[tool] uvicorn not found in container. Ensure dependencies are installed." >&2
  exit 127
fi

log_info "[tool] Starting server..."
"${UVICORN_CMD[@]}" &
SERVER_PID=$!

# Run warmup in background
"${SCRIPT_DIR}/warmup.sh" &

# Wait on server (container stays alive)
wait "${SERVER_PID}"
