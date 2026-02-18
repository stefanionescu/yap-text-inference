#!/usr/bin/env bash
# =============================================================================
# CLI Argument Utilities
# =============================================================================
# Provides utility functions for normalizing engine names and validating
# deploy modes from command-line arguments.

_CLI_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../config/values/core.sh
source "${_CLI_DIR}/../../config/values/core.sh"
# shellcheck source=../../config/patterns.sh
source "${_CLI_DIR}/../../config/patterns.sh"

cli_normalize_engine() {
  local engine="${1:-${CFG_DEFAULT_ENGINE}}"
  case "${engine}" in
    "${CFG_ENGINE_VLLM}" | VLLM)
      echo "${CFG_ENGINE_VLLM}"
      ;;
    "${CFG_ENGINE_TRT}" | TRT | tensorrt | TENSORRT | trtllm | TRTLLM)
      echo "${CFG_ENGINE_TRT}"
      ;;
    *)
      return 1
      ;;
  esac
}

cli_validate_deploy_mode() {
  local mode="${1:-${CFG_DEFAULT_DEPLOY_MODE}}"
  case "${mode}" in
    "${CFG_DEPLOY_MODE_BOTH}" | "${CFG_DEPLOY_MODE_CHAT}" | "${CFG_DEPLOY_MODE_TOOL}")
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
