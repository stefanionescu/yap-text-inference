#!/usr/bin/env bash

# Shared Hugging Face helpers

hf_enable_transfer() {
  local prefix="${1:-[hf]}"
  local py_bin="${2:-python3}"

  if "${py_bin}" -c "import hf_transfer" >/dev/null 2>&1; then
    export HF_HUB_ENABLE_HF_TRANSFER=1
    return 0
  fi

  export HF_HUB_ENABLE_HF_TRANSFER=0
  if type log_warn >/dev/null 2>&1; then
    log_warn "${prefix} ⚠ hf_transfer not installed, using standard downloads"
  else
    echo "${prefix} ⚠ hf_transfer not installed, using standard downloads" >&2
  fi
  return 1
}
