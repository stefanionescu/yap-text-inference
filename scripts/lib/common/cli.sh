#!/usr/bin/env bash

cli_normalize_engine() {
  local engine="${1:-trt}"
  case "${engine}" in
    vllm|VLLM)
      echo "vllm"
      ;;
    trt|TRT|tensorrt|TENSORRT|trtllm|TRTLLM)
      echo "trt"
      ;;
    *)
      return 1
      ;;
  esac
}

cli_validate_deploy_mode() {
  local mode="${1:-both}"
  case "${mode}" in
    both|chat|tool)
      echo "${mode}"
      ;;
    *)
      return 1
      ;;
  esac
}

cli_set_engine_value() {
  local value="$1"
  local context="$2"
  # shellcheck disable=SC2034  # nameref variable assigned for caller
  local -n engine_ref="$3"
  if [ -z "${value}" ]; then
    log_err "${context} ✗ --engine requires a value (trt|vllm)"
    return 1
  fi
  # shellcheck disable=SC2034  # nameref variable assigned for caller
  engine_ref="${value}"
  return 0
}

cli_set_deploy_mode_value() {
  local value="$1"
  local context="$2"
  # shellcheck disable=SC2034  # nameref variable assigned for caller
  local -n deploy_ref="$3"
  if [ -z "${value}" ]; then
    log_err "${context} ✗ --deploy-mode requires a value (both|chat|tool)"
    return 1
  fi
  if ! value="$(cli_validate_deploy_mode "${value}")"; then
    log_err "${context} ✗ Invalid deploy mode '${value}'. Expected both|chat|tool."
    return 1
  fi
  # shellcheck disable=SC2034  # nameref variable assigned for caller
  deploy_ref="${value}"
  return 0
}
