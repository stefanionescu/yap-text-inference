#!/usr/bin/env bash
# vLLM runtime detection.
#
# Detects runtime capabilities like FlashInfer. Quantization is auto-detected
# from CHAT_MODEL name by Python (src/config/engine.py).

_RUNTIME_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Detect FlashInfer availability (optional fast-path)
HAS_FLASHINFER=0
if [ -f "/opt/venv/bin/python" ]; then
  PY_BIN="/opt/venv/bin/python"
elif [ -f "${_RUNTIME_SCRIPT_DIR}/../../.venv/bin/python" ]; then
  PY_BIN="${_RUNTIME_SCRIPT_DIR}/../../.venv/bin/python"
elif command -v python >/dev/null 2>&1; then
  PY_BIN="python"
else
  PY_BIN=""
fi

if [ -n "${PY_BIN}" ]; then
  if "${PY_BIN}" - <<'PY' >/dev/null 2>&1; then
try:
    import flashinfer  # noqa: F401
except Exception:
    raise SystemExit(1)
PY
    HAS_FLASHINFER=1
  fi
fi
export HAS_FLASHINFER
