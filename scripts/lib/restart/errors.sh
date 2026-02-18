#!/usr/bin/env bash
# =============================================================================
# Restart Error Messaging Helpers
# =============================================================================

_RESTART_ERRORS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../config/messages/restart.sh
source "${_RESTART_ERRORS_DIR}/../../config/messages/restart.sh"

restart_err_prequant_push_quant() {
  local source_model="${1:-unknown}"
  log_err "${CFG_RESTART_ERR_PREQUANT_PUSH_QUANT}"
  log_errf "${CFG_RESTART_ERR_PREQUANT_MODEL_IS_QUANTIZED}" "${source_model}"
  log_err "${CFG_RESTART_ERR_PREQUANT_NO_ARTIFACTS}"
  log_blank
  log_err "[restart]   Options:"
  log_err "${CFG_RESTART_ERR_PREQUANT_OPTION_1}"
  log_err "${CFG_RESTART_ERR_PREQUANT_OPTION_2}"
}

restart_err_no_awq_sources() {
  local deploy_mode="${1:-${CFG_DEFAULT_DEPLOY_MODE}}"
  log_errf "${CFG_RESTART_ERR_AWQ_NOT_FOUND}" "${deploy_mode}"
  log_blank
  log_err "[restart] Options:"
  log_err "${CFG_RESTART_ERR_AWQ_OPTION_1}"
  log_errf "${CFG_RESTART_ERR_AWQ_OPTION_2}" "${ROOT_DIR}"
}

restart_err_missing_trt_engine() {
  local deploy_mode="${1:-${CFG_DEFAULT_DEPLOY_MODE}}"
  local trt_engine_dir="${TRT_ENGINE_DIR:-<empty>}"

  log_err "${CFG_RESTART_ERR_TRT_ENGINE_MISSING}"
  log_errf "${CFG_RESTART_ERR_TRT_ENGINE_DIR}" "${trt_engine_dir}"
  log_blank
  log_err "[restart]   TensorRT-LLM requires a pre-built engine. Options:"
  log_err "${CFG_RESTART_ERR_TRT_ENGINE_OPTION_1}"
  log_errf "${CFG_RESTART_ERR_TRT_ENGINE_OPTION_2}" "${deploy_mode}"
  log_err "${CFG_RESTART_ERR_TRT_ENGINE_OPTION_3}"
}
