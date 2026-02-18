#!/usr/bin/env bash
# shellcheck disable=SC1091
# =============================================================================
# Restart Reconfiguration Helpers
# =============================================================================
# Functions for reconfiguring models and quantization during restart without
# reinstalling dependencies. Handles model identity resolution, cache
# preservation decisions, and quantization pipeline execution.

RESTART_RECONFIG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${RESTART_RECONFIG_DIR}/../../common/model/detect.sh"
source "${RESTART_RECONFIG_DIR}/../../main/quant.sh"
source "${RESTART_RECONFIG_DIR}/../../../config/values/core.sh"
source "${RESTART_RECONFIG_DIR}/../../../config/values/runtime.sh"
source "${RESTART_RECONFIG_DIR}/../../../config/values/quantization.sh"
source "${RESTART_RECONFIG_DIR}/../../../config/patterns.sh"

_restart_resolve_deploy_mode() {
  local candidate="${RECONFIG_DEPLOY_MODE:-${DEPLOY_MODE:-${CFG_DEFAULT_DEPLOY_MODE}}}"
  candidate="${candidate,,}"
  case "${candidate}" in
    "${CFG_DEPLOY_MODE_BOTH}" | "${CFG_DEPLOY_MODE_CHAT}" | "${CFG_DEPLOY_MODE_TOOL}")
      echo "${candidate}"
      ;;
    *)
      log_err "[restart] ✗ Invalid deploy mode '${candidate}'. Use --deploy-mode both|chat|tool."
      return 1
      ;;
  esac
}

_restart_is_gptq_model() {
  is_gptq_name "$1"
}

_restart_is_awq_model() {
  is_awq_name "$1"
}

_restart_autodetect_quantization() {
  local chat_model="$1"
  local chat_enabled="$2"

  if [ "${chat_enabled}" = "1" ]; then
    local chat_hint
    chat_hint="$(get_quantization_hint "${chat_model}")"
    if [ "${chat_hint}" = "${CFG_QUANT_MODE_4BIT_BACKEND}" ]; then
      echo "${CFG_QUANT_MODE_4BIT_BACKEND}"
      return
    fi
    if [ "${chat_hint}" = "${CFG_QUANT_MODE_GPTQ_BACKEND}" ]; then
      echo "${CFG_QUANT_MODE_GPTQ_BACKEND}"
      return
    fi
  fi

  # Return "8bit" placeholder; resolved to fp8 or int8 based on GPU in quantization.sh
  echo "${CFG_QUANT_MODE_8BIT_PLACEHOLDER}"
}

_restart_normalize_quantization_flag() {
  local value="${1:-}"
  if [ -z "${value}" ]; then
    echo ""
    return
  fi
  local lowered="${value,,}"
  case "${lowered}" in
    "${CFG_QUANT_MODE_4BIT_PLACEHOLDER}")
      # 4-bit always maps to AWQ runtime
      echo "${CFG_QUANT_MODE_4BIT_BACKEND}"
      ;;
    "${CFG_QUANT_MODE_8BIT_PLACEHOLDER}")
      # Return "8bit" placeholder; resolved to fp8 or int8 based on GPU in quantization.sh
      echo "${CFG_QUANT_MODE_8BIT_PLACEHOLDER}"
      ;;
    *)
      echo "${value}"
      ;;
  esac
}

_restart_validate_quantization() {
  local value="$1"
  case "${value}" in
    "${CFG_QUANT_MODE_8BIT_PLACEHOLDER}" | "${CFG_QUANT_MODE_FP8_BACKEND}" | "${CFG_QUANT_MODE_4BIT_BACKEND}" | "${CFG_QUANT_MODE_GPTQ_ALIAS}" | "${CFG_QUANT_MODE_GPTQ_BACKEND}")
      return 0
      ;;
    *)
      log_err "[restart] ✗ Invalid quantization '${value}'. Expected 8bit|fp8|gptq|gptq_marlin|awq."
      return 1
      ;;
  esac
}

_restart_needs_awq_pipeline() {
  if [ "${CHAT_QUANTIZATION:-}" = "${CFG_QUANT_MODE_4BIT_BACKEND}" ]; then
    return 0
  fi
  return 1
}

# TRT engine always requires a build step (AWQ, FP8, INT8 - all need compiled engines)
_restart_needs_trt_engine_build() {
  if [ "${INFERENCE_ENGINE:-${CFG_DEFAULT_RUNTIME_ENGINE}}" = "${CFG_ENGINE_TRT}" ]; then
    # Check if engine directory exists and is valid
    local trt_env_file="${ROOT_DIR}/${CFG_RUNTIME_TRT_ENGINE_ENV_FILE}"
    if [ -f "${trt_env_file}" ]; then
      # shellcheck disable=SC1090
      source "${trt_env_file}"
      if [ -n "${TRT_ENGINE_DIR:-}" ] && [ -d "${TRT_ENGINE_DIR}" ]; then
        # Engine exists - no need to rebuild
        return 1
      fi
    fi
    # No valid engine found - need to build
    return 0
  fi
  return 1
}

_restart_resolve_model_identity() {
  local value="$1"
  if [ -z "${value:-}" ]; then
    echo ""
    return
  fi
  if [[ ${value} == "${ROOT_DIR}/.awq/"* ]]; then
    local source
    source="$(_awq_read_source_model "${value}")"
    if [ -n "${source}" ]; then
      echo "${source}"
      return
    fi
  fi
  echo "${value}"
}

_restart_load_previous_config() {
  PREV_CONFIG_FOUND=0
  PREV_CHAT_MODEL=""
  PREV_TOOL_MODEL=""
  PREV_CHAT_QUANTIZATION=""
  PREV_DEPLOY_MODE=""
  PREV_DEPLOY_CHAT=0
  PREV_DEPLOY_TOOL=0

  local last_env="${ROOT_DIR}/${CFG_RUNTIME_LAST_CONFIG_FILE}"
  if [ ! -f "${last_env}" ]; then
    return
  fi

  PREV_CONFIG_FOUND=1

  local cur_chat="${CHAT_MODEL:-}"
  local cur_tool="${TOOL_MODEL:-}"
  local cur_chat_quant="${CHAT_QUANTIZATION:-}"
  local cur_deploy="${DEPLOY_MODE:-}"
  # shellcheck disable=SC1090
  source "${last_env}" || true

  PREV_CHAT_MODEL="${CHAT_MODEL:-}"
  PREV_TOOL_MODEL="${TOOL_MODEL:-}"
  PREV_CHAT_QUANTIZATION="${CHAT_QUANTIZATION:-}"
  PREV_DEPLOY_MODE="${DEPLOY_MODE:-}"
  case "${PREV_DEPLOY_MODE}" in
    "${CFG_DEPLOY_MODE_BOTH}")
      PREV_DEPLOY_CHAT=1
      PREV_DEPLOY_TOOL=1
      ;;
    "${CFG_DEPLOY_MODE_CHAT}")
      PREV_DEPLOY_CHAT=1
      PREV_DEPLOY_TOOL=0
      ;;
    "${CFG_DEPLOY_MODE_TOOL}")
      PREV_DEPLOY_CHAT=0
      PREV_DEPLOY_TOOL=1
      ;;
    *)
      PREV_DEPLOY_CHAT=0
      PREV_DEPLOY_TOOL=0
      ;;
  esac

  CHAT_MODEL="${cur_chat}"
  TOOL_MODEL="${cur_tool}"
  CHAT_QUANTIZATION="${cur_chat_quant}"
  DEPLOY_MODE="${cur_deploy}"

}

_restart_can_preserve_cache() {
  local deploy_chat="$1"
  local deploy_tool="$2"

  if [ "${PREV_CONFIG_FOUND}" != "1" ]; then
    return 1
  fi

  if [ "${deploy_chat}" != "${PREV_DEPLOY_CHAT}" ]; then
    return 1
  fi
  if [ "${deploy_tool}" != "${PREV_DEPLOY_TOOL}" ]; then
    return 1
  fi

  if [ "${deploy_chat}" = "1" ]; then
    local prev_chat_id new_chat_id
    prev_chat_id="$(_restart_resolve_model_identity "${PREV_CHAT_MODEL}")"
    new_chat_id="$(_restart_resolve_model_identity "${CHAT_MODEL}")"
    if [ -z "${prev_chat_id}" ] || [ "${new_chat_id}" != "${prev_chat_id}" ]; then
      return 1
    fi
    if [ "${CHAT_QUANTIZATION:-}" != "${PREV_CHAT_QUANTIZATION:-}" ]; then
      return 1
    fi
  fi

  if [ "${deploy_tool}" = "1" ]; then
    local prev_tool_id new_tool_id
    prev_tool_id="$(_restart_resolve_model_identity "${PREV_TOOL_MODEL}")"
    new_tool_id="$(_restart_resolve_model_identity "${TOOL_MODEL}")"
    if [ -z "${prev_tool_id}" ] || [ "${new_tool_id}" != "${prev_tool_id}" ]; then
      return 1
    fi
  fi

  return 0
}
