#!/usr/bin/env bash
set -euo pipefail

# Inline warmup/bench for AWQ image.
# Prints directly to console; never fails the container.

SERVER_ADDR="127.0.0.1:${PORT:-8000}"
MAX_BATCH="${TRTLLM_MAX_BATCH_SIZE:-16}"
resolve_concurrency() {
  local target="$1"
  local max_batch="$2"
  local c="$target"
  if ((c > max_batch)); then
    c=$max_batch
  fi
  if ((c < 1)); then
    c=1
  fi
  echo "$c"
}

echo "[warmup] Waiting for server readiness at http://${SERVER_ADDR} ..."
ready=0
for ((i = 1; i <= 90; i++)); do
  if curl -fsS "http://${SERVER_ADDR}/healthz" >/dev/null 2>&1 || curl -fsS "http://${SERVER_ADDR}/health" >/dev/null 2>&1; then
    ready=1
    break
  fi
  if ((i % 15 == 0)); then
    echo "[warmup] still waiting for server (attempt ${i}/90)..."
  fi
  sleep 2
done

if [[ $ready -ne 1 ]]; then
  echo "[warmup] WARN: server not ready within timeout; skipping tests"
  exit 0
fi

voices=(female male)

# Warmup per voice
for v in "${voices[@]}"; do
  echo "[warmup] warmup voice=${v}"
  python /app/tests/warmup.py --server "${SERVER_ADDR}" --voice "${v}" --api-key "${ORPHEUS_API_KEY}" || true
  sleep 1
done

declare -a TARGETS=()
if ((MAX_BATCH == 7)); then
  TARGETS=(7)
else
  TARGETS=(8)
  if ((MAX_BATCH >= 16)); then
    TARGETS+=(16)
  fi
  TARGETS+=("$MAX_BATCH")
fi

for target in "${TARGETS[@]}"; do
  conc=$(resolve_concurrency "$target" "$MAX_BATCH")
  total="$conc"
  for v in "${voices[@]}"; do
    echo "[bench] ${target}x${target} voice=${v} (n=${total}, concurrency=${conc})"
    python /app/tests/bench.py --server "${SERVER_ADDR}" --n "${total}" --concurrency "${conc}" --voice "${v}" --api-key "${ORPHEUS_API_KEY}" || true
    sleep 1
  done
done

echo "[warmup] Completed post-start tests."
exit 0
