#!/usr/bin/env bash

# Centralized helpers for suppressing noisy Python warnings.

python_warning_add_filter() {
  local filter="${1:-}"
  if [ -z "${filter}" ]; then
    return 0
  fi

  if [ -z "${PYTHONWARNINGS:-}" ]; then
    export PYTHONWARNINGS="${filter}"
  elif ! printf '%s' "${PYTHONWARNINGS}" | grep -Fq -- "${filter}"; then
    export PYTHONWARNINGS="${PYTHONWARNINGS},${filter}"
  fi
}

python_warning_suppress_pynvml_future() {
  # Note: PYTHONWARNINGS treats the message field as literal (regex chars escaped),
  # so match the fixed prefix emitted by torch when importing pynvml.
  local filter="ignore:The pynvml package is deprecated.:FutureWarning"
  python_warning_add_filter "${filter}"
}

python_warning_suppress_modelopt_lm_head_warning() {
  # TRT quantization prints a redundant user warning about lm_head accuracy loss.
  local filter="ignore:Enable lm_head quantization. lm_head quantization may lead to additional accuracy loss.:UserWarning"
  python_warning_add_filter "${filter}"
}

python_warning_suppress_pynvml_future
python_warning_suppress_modelopt_lm_head_warning
