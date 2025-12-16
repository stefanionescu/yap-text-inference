#!/usr/bin/env bash

# Ensure QUANTIZATION is set (Docker vLLM AWQ stack defaults to 'awq')
export QUANTIZATION=${QUANTIZATION:-awq}

# Detect FlashInfer availability (optional fast-path)
HAS_FLASHINFER=0
if [ -f "/opt/venv/bin/python" ]; then
  PY_BIN="/opt/venv/bin/python"
elif [ -f "${SCRIPT_DIR}/../../.venv/bin/python" ]; then
  PY_BIN="${SCRIPT_DIR}/../../.venv/bin/python"
elif command -v python >/dev/null 2>&1; then
  PY_BIN="python"
else
  PY_BIN=""
fi

if [ -n "${PY_BIN}" ]; then
  if "${PY_BIN}" - <<'PY' >/dev/null 2>&1
try:
    import flashinfer  # noqa: F401
except Exception:
    raise SystemExit(1)
PY
  then
    HAS_FLASHINFER=1
  fi
fi
export HAS_FLASHINFER

