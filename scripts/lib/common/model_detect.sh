#!/usr/bin/env bash

# Helper utilities for inferring quantization hints from model identifiers.

_model_detect_lower() {
  local value="${1:-}"
  if [ -z "${value}" ]; then
    echo ""
    return
  fi
  if [[ -n "${BASH_VERSION:-}" && "${BASH_VERSION%%.*}" -ge 4 ]]; then
    echo "${value,,}"
  else
    echo "${value}" | tr '[:upper:]' '[:lower:]'
  fi
}

_model_detect_has_marker() {
  local lowered="$1"
  local marker="$2"
  [[ "${lowered}" == *"${marker}"* ]]
}

_model_detect_has_any_marker() {
  local lowered="$1"
  shift
  local marker
  for marker in "$@"; do
    if _model_detect_has_marker "${lowered}" "${marker}"; then
      return 0
    fi
  done
  return 1
}

model_detect_is_gptq_name() {
  local value="${1:-}"
  local lowered
  lowered="$(_model_detect_lower "${value}")"
  if [ -z "${lowered}" ]; then
    return 1
  fi
  _model_detect_has_marker "${lowered}" "gptq"
}

model_detect_has_w4a16_hint() {
  local value="${1:-}"
  local lowered
  lowered="$(_model_detect_lower "${value}")"
  if [ -z "${lowered}" ]; then
    return 1
  fi
  _model_detect_has_any_marker "${lowered}" \
    "w4a16" \
    "nvfp4" \
    "compressed-tensors" \
    "autoround"
}

model_detect_is_awq_name() {
  local value="${1:-}"
  local lowered
  lowered="$(_model_detect_lower "${value}")"
  if [ -z "${lowered}" ]; then
    return 1
  fi
  if _model_detect_has_marker "${lowered}" "awq"; then
    return 0
  fi
  model_detect_has_w4a16_hint "${lowered}"
}

model_detect_classify_prequant() {
  local value="${1:-}"
  if model_detect_is_awq_name "${value}"; then
    echo "awq"
    return
  fi
  if model_detect_is_gptq_name "${value}"; then
    echo "gptq"
    return
  fi
  echo ""
}

model_detect_quantization_hint() {
  local classification
  classification="$(model_detect_classify_prequant "$1")"
  case "${classification}" in
    awq) echo "awq" ;;
    gptq) echo "gptq_marlin" ;;
    *) echo "" ;;
  esac
}

model_detect_is_prequant_awq() {
  local value="${1:-}"
  if [ -z "${value}" ]; then
    return 1
  fi
  if model_detect_is_awq_name "${value}"; then
    return 0
  fi
  if [ -d "${value}" ] && { [ -f "${value}/awq_metadata.json" ] || [ -f "${value}/awq_config.json" ]; }; then
    return 0
  fi
  return 1
}


