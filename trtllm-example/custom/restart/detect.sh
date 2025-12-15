#!/usr/bin/env bash

# Engine and quantization auto-detection for custom/restart.sh
# Exports: DETECTED_ENGINE_DIR, DETECTED_QUANTIZATION

_log_info() { echo "[restart:detect] $*"; }
_log_warn() { echo "[restart:detect] WARN: $*"; }

_is_engine_dir() {
  local d="$1"
  if [ -z "$d" ]; then return 1; fi
  if [ -f "$d/rank0.engine" ]; then return 0; fi
  # allow pointing inside engines/<label>/runtime/ engine layout
  if [ -f "$d/../build_metadata.json" ]; then return 0; fi
  return 1
}

_quant_from_metadata() {
  local d="$1"
  local meta="$d/build_metadata.json"
  if [ ! -f "$meta" ]; then
    # try parent folder
    meta="$d/../build_metadata.json"
  fi
  if [ -f "$meta" ]; then
    local summary
    summary=$(
      python - "$meta" <<'PY' 2>/dev/null | tr -d '\r' | tr -d '\n'
import json, sys
path = sys.argv[1]
try:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
except Exception:
    print("")
    raise SystemExit(0)
mode = (data.get("precision_mode") or "").lower()
q = data.get("quantization") or {}
weights = (q.get("weights") or "").lower()
kv = (q.get("kv_cache") or "").lower()
dtype = (data.get("dtype") or "").lower()
if mode == "base" and weights:
    print(f"base-{weights}")
elif weights == "int4_awq":
    print("int4-awq")
elif weights:
    print(weights)
elif dtype:
    print(dtype)
else:
    print("")
PY
    )
    if [ -n "$summary" ]; then
      echo "$summary"
      return 0
    fi
  fi
  # Path heuristics
  case "$d" in
    *int4-awq* | *awq*) echo "int4-awq" ;;
    *fp16* | *float16*) echo "fp16" ;;
    *fp8* | *float8*) echo "fp8" ;;
    *) echo "unknown" ;;
  esac
}

restart_detect_engine() {
  DETECTED_ENGINE_DIR=""
  DETECTED_QUANTIZATION="unknown"

  # 1) Honor explicit env if valid
  if _is_engine_dir "${TRTLLM_ENGINE_DIR:-}"; then
    DETECTED_ENGINE_DIR="${TRTLLM_ENGINE_DIR}"
    DETECTED_QUANTIZATION="$(_quant_from_metadata "${DETECTED_ENGINE_DIR}")"
    _log_info "Using engine from TRTLLM_ENGINE_DIR='${DETECTED_ENGINE_DIR}' (quant='${DETECTED_QUANTIZATION}')"
    export DETECTED_ENGINE_DIR DETECTED_QUANTIZATION
    return 0
  fi

  # 2) Common defaults
  local candidates=(
    "$PWD/models/orpheus-trt-awq"
    "$PWD/models/trt-llm/engines"
  )
  # 3) Any directory under models/ containing rank0.engine
  if [ -d "$PWD/models" ]; then
    while IFS= read -r -d '' f; do
      candidates+=("$(dirname "$f")")
    done < <(find "$PWD/models" -type f -name 'rank0.engine' -print0 2>/dev/null || true)
  fi

  local c
  for c in "${candidates[@]}"; do
    if _is_engine_dir "$c"; then
      DETECTED_ENGINE_DIR="$c"
      DETECTED_QUANTIZATION="$(_quant_from_metadata "$c")"
      _log_info "Detected engine at '${DETECTED_ENGINE_DIR}' (quant='${DETECTED_QUANTIZATION}')"
      export DETECTED_ENGINE_DIR DETECTED_QUANTIZATION
      return 0
    fi
  done

  _log_warn "No engine dir found in defaults; trying last known config..."
  if [ -f "$PWD/.run/last_config.env" ]; then
    # shellcheck disable=SC1090,SC1091
    source "$PWD/.run/last_config.env" || true
    if _is_engine_dir "${TRTLLM_ENGINE_DIR:-}"; then
      DETECTED_ENGINE_DIR="${TRTLLM_ENGINE_DIR}"
      DETECTED_QUANTIZATION="$(_quant_from_metadata "${DETECTED_ENGINE_DIR}")"
      _log_info "Using engine from .run/last_config.env: '${DETECTED_ENGINE_DIR}'"
      export DETECTED_ENGINE_DIR DETECTED_QUANTIZATION
      return 0
    fi
  fi

  return 1
}
