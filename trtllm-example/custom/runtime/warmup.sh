#!/usr/bin/env bash
set -euo pipefail

# Post-start smoke and load tests for the TTS server.
# - Waits for server readiness
# - Runs warmup, bench (8,8), bench (16,16)
# - Suppresses detailed test output; writes concise results

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

RUN_DIR=".run"
LOG_DIR="logs"
mkdir -p "$RUN_DIR" "$LOG_DIR"

LOCK_FILE="$RUN_DIR/post_start_tests.lock"
DONE_FILE="$RUN_DIR/post_start_tests.done"
OUT_SUMMARY="$LOG_DIR/post_start_tests.log"

# Allow overriding the readiness wait window (default 20 minutes).
# e.g. SERVER_READY_TIMEOUT_SECONDS=600 bash custom/runtime/warmup.sh
HOST_VAL="${HOST:-127.0.0.1}"
if [[ $HOST_VAL == "0.0.0.0" || $HOST_VAL == "::" ]]; then
  HOST_VAL="127.0.0.1"
fi
PORT_VAL="${PORT:-8000}"
SERVER_ADDR="${HOST_VAL}:${PORT_VAL}"
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

# Helper: wait for health endpoint
wait_for_ready() {
  local url1="http://${SERVER_ADDR}/healthz"
  local url2="http://${SERVER_ADDR}/health"
  local timeout_s="${SERVER_READY_TIMEOUT_SECONDS:-1200}"
  local start_ts
  start_ts=$(date +%s)
  while true; do
    python - "$url1" "$url2" <<'PY' >/dev/null 2>&1 && return 0
import sys, urllib.request
for u in sys.argv[1:]:
    try:
        with urllib.request.urlopen(u, timeout=2) as r:
            if r.status == 200:
                raise SystemExit(0)
    except Exception:
        pass
raise SystemExit(1)
PY
    if (($(date +%s) - start_ts >= timeout_s)); then
      return 1
    fi
    sleep 2
  done
}

log() {
  local line
  line="[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] $*"
  echo "$line" | tee -a "$OUT_SUMMARY"
}

log "Post-start tests: waiting for server at ${SERVER_ADDR}..."
if ! wait_for_ready; then
  log "ERROR: Server not ready within timeout."
  rm -f "$LOCK_FILE"
  exit 0
fi
log "Server ready. Running tests..."

ok=1

# Voices to test
VOICES=(female male)

# Warmup per voice
for v in "${VOICES[@]}"; do
  VLOG="${LOG_DIR}/test_warmup_${v}.log"
  if ! python tests/warmup.py --server "$SERVER_ADDR" --voice "$v" --api-key "${ORPHEUS_API_KEY}" >"$VLOG" 2>&1; then
    log "FAIL: warmup ($v) failed (see $VLOG)"
    ok=0
  else
    log "OK: warmup ($v)"
  fi
  sleep 1
done

# Bench workloads per voice (include max batch check)
declare -a TARGETS=()
TARGETS=("$MAX_BATCH")
if ((MAX_BATCH == 7)); then
  TARGETS+=("7")
else
  TARGETS+=(8)
  if ((MAX_BATCH >= 16)); then
    TARGETS+=(16)
  fi
fi

for target in "${TARGETS[@]}"; do
  conc=$(resolve_concurrency "$target" "$MAX_BATCH")
  total="$conc"
  label="${target}x${target}"
  if ((conc == MAX_BATCH)); then
    label="${target}x${target} (max=${conc})"
  fi
  [[ $conc -ne $target ]] && label="${label} (capped at ${conc})"
  for v in "${VOICES[@]}"; do
    VLOG="${LOG_DIR}/test_bench_${target}x${target}_${v}.log"
    if ! python tests/bench.py --server "$SERVER_ADDR" --n "$total" --concurrency "$conc" --voice "$v" --api-key "${ORPHEUS_API_KEY}" >"$VLOG" 2>&1; then
      log "FAIL: bench ${label} ($v) exited non-zero (see $VLOG)"
      ok=0
    else
      if grep -E "Errors: .*\(busy=[0-9]+, other=([0-9]+)\)" -o "$VLOG" | grep -Eq "other=0"; then
        log "OK: bench ${label} ($v)"
      else
        log "WARN: bench ${label} ($v) reported non-zero other errors (see $VLOG)"
        ok=0
      fi
    fi
    sleep 1
  done
done

if [[ $ok -eq 1 ]]; then
  log "SUCCESS: All post-start tests passed."
else
  log "COMPLETE: Post-start tests finished with failures."
fi

rm -f "$LOCK_FILE" "$DONE_FILE"
echo "done" >"$DONE_FILE"
exit 0
