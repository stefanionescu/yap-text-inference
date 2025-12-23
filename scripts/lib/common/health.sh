#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: health.sh <url...>" >&2
  exit 1
fi

timeout_val="${WARMUP_HEALTH_TIMEOUT:-2}"
if ! [[ "${timeout_val}" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
  timeout_val=2
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "[health] curl is required for health probes" >&2
  exit 1
fi

for url in "$@"; do
  if curl \
      --silent \
      --show-error \
      --fail \
      --max-time "${timeout_val}" \
      --connect-timeout "${timeout_val}" \
      "${url}" >/dev/null 2>&1; then
    exit 0
  fi
done

exit 1

