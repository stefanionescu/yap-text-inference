#!/usr/bin/env bash
# shellcheck disable=SC1091
# =============================================================================
# Restart Reconfiguration Actions
# =============================================================================
# Orchestrates reconfigure flow and requires helpers from helpers.sh.

RESTART_RECONFIG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${RESTART_RECONFIG_DIR}/helpers.sh"
source "${RESTART_RECONFIG_DIR}/../../../config/values/core.sh"
source "${RESTART_RECONFIG_DIR}/../../../config/values/runtime.sh"
source "${RESTART_RECONFIG_DIR}/../../../config/patterns.sh"
source "${RESTART_RECONFIG_DIR}/../../../config/messages/restart.sh"

clear_model_artifacts() {
  rm -f "${ROOT_DIR}/${CFG_RUNTIME_TRT_ENGINE_ENV_FILE}" 2>/dev/null || true

  local deploy_mode="${DEPLOY_MODE:-${CFG_DEFAULT_DEPLOY_MODE}}"
  local model_paths=(
    "${ROOT_DIR}/.awq"
    "${ROOT_DIR}/.trt_cache"
    "${ROOT_DIR}/models"
  )

  if [ "${deploy_mode}" = "${CFG_DEPLOY_MODE_TOOL}" ] ||
    [ "${INFERENCE_ENGINE:-${CFG_DEFAULT_RUNTIME_ENGINE}}" != "${CFG_ENGINE_VLLM}" ]; then
    model_paths+=(
      "${ROOT_DIR}/.vllm_cache"
      "${ROOT_DIR}/.flashinfer"
      "${ROOT_DIR}/.xformers"
    )
  fi

  if [ "${deploy_mode}" = "${CFG_DEPLOY_MODE_TOOL}" ] ||
    [ "${INFERENCE_ENGINE:-${CFG_DEFAULT_RUNTIME_ENGINE}}" != "${CFG_ENGINE_TRT}" ]; then
    model_paths+=("${ROOT_DIR}/.trtllm-repo")
  fi

  local hf_paths=(
    "${ROOT_DIR}/.hf"
    "${HF_HOME:-}"
    "${HUGGINGFACE_HUB_CACHE:-}"
    "${TRANSFORMERS_CACHE:-}"
    "$HOME/.cache/huggingface"
    "$HOME/.cache/huggingface/hub"
    "$HOME/.huggingface"
    "$HOME/.config/huggingface"
    "$HOME/.local/share/huggingface"
  )

  local path
  for path in "${model_paths[@]}" "${hf_paths[@]}"; do
    if [ -n "${path}" ] && [ -e "${path}" ]; then
      rm -rf "${path}" || true
    fi
  done
}

_restart_set_deploy_targets() {
  RESTART_DEPLOY_CHAT=0
  RESTART_DEPLOY_TOOL=0
  case "${DEPLOY_MODE}" in
    "${CFG_DEPLOY_MODE_BOTH}")
      RESTART_DEPLOY_CHAT=1
      RESTART_DEPLOY_TOOL=1
      ;;
    "${CFG_DEPLOY_MODE_CHAT}") RESTART_DEPLOY_CHAT=1 ;;
    "${CFG_DEPLOY_MODE_TOOL}") RESTART_DEPLOY_TOOL=1 ;;
  esac
}

_restart_validate_requested_models() {
  RESTART_CHAT_MODEL="${RECONFIG_CHAT_MODEL:-${CHAT_MODEL:-}}"
  RESTART_TOOL_MODEL="${RECONFIG_TOOL_MODEL:-${TOOL_MODEL:-}}"

  if [ "${RESTART_DEPLOY_CHAT}" = "1" ] && [ -z "${RESTART_CHAT_MODEL}" ]; then
    log_err "[restart] ✗ Chat deployment requested but no chat model supplied."
    log_err "[restart] ✗ Pass --chat-model <repo_or_path> or export CHAT_MODEL before running --reset-models."
    return 1
  fi
  if [ "${RESTART_DEPLOY_TOOL}" = "1" ] && [ -z "${RESTART_TOOL_MODEL}" ]; then
    log_err "[restart] ✗ Tool deployment requested but no tool model supplied."
    log_err "[restart] ✗ Pass --tool-model <repo_or_path> or export TOOL_MODEL before running --reset-models."
    return 1
  fi
  if ! validate_push_quant_prequant "${RESTART_CHAT_MODEL}" "${RESTART_TOOL_MODEL}" "${HF_AWQ_PUSH_REQUESTED:-0}" "[restart]"; then
    return 1
  fi
  return 0
}

_restart_export_requested_models() {
  if [ "${RESTART_DEPLOY_CHAT}" = "1" ]; then
    export CHAT_MODEL="${RESTART_CHAT_MODEL}"
    export CHAT_MODEL_NAME="${RESTART_CHAT_MODEL}"
  else
    unset CHAT_MODEL CHAT_MODEL_NAME
  fi

  if [ "${RESTART_DEPLOY_TOOL}" = "1" ]; then
    export TOOL_MODEL="${RESTART_TOOL_MODEL}"
    export TOOL_MODEL_NAME="${RESTART_TOOL_MODEL}"
  else
    unset TOOL_MODEL TOOL_MODEL_NAME
  fi
}

_restart_prepare_quantization() {
  local chat_quant="${RECONFIG_CHAT_QUANTIZATION:-${CHAT_QUANTIZATION:-}}"
  if [ -n "${chat_quant}" ]; then
    chat_quant="$(_restart_normalize_quantization_flag "${chat_quant}" "${RESTART_CHAT_MODEL}")"
    _restart_validate_quantization "${chat_quant}" || return 1
  fi

  local chat_hint=""
  if [ "${RESTART_DEPLOY_CHAT}" = "1" ]; then
    chat_hint="$(get_quantization_hint "${RESTART_CHAT_MODEL}")"
  fi

  quant_resolve_settings \
    "${DEPLOY_MODE}" \
    "${RESTART_CHAT_MODEL}" \
    "${RECONFIG_CHAT_QUANTIZATION:-}" \
    "${chat_hint}" \
    "${chat_quant}"

  push_quant_apply_policy "${CHAT_QUANTIZATION:-}" "restart"
  validate_push_quant_prereqs "${DEPLOY_MODE}" || return 1
  push_engine_apply_policy "${INFERENCE_ENGINE:-${CFG_DEFAULT_ENGINE}}" "restart"
  validate_push_engine_prereqs || return 1
  validate_models_early
}

_restart_prepare_runtime() {
  RESTART_PRESERVE_CACHE=0
  if _restart_can_preserve_cache "${RESTART_DEPLOY_CHAT}" "${RESTART_DEPLOY_TOOL}"; then
    RESTART_PRESERVE_CACHE=1
  fi

  log_section "[restart] Reconfiguring models..."
  RESTART_RESOLVED_VENV="${VENV_DIR:-$(get_venv_dir)}"
  NUKE_ALL=0 "${SCRIPT_DIR}/stop.sh"

  if [ "${RESTART_PRESERVE_CACHE}" != "1" ]; then
    clear_model_artifacts
  fi

  apply_defaults_and_deps
  if [ -d "${RESTART_RESOLVED_VENV}" ]; then
    return 0
  fi

  log_err "[restart] ✗ Virtual environment missing at ${RESTART_RESOLVED_VENV}"
  log_err "[restart] ✗ Re-run with --install-deps to rebuild dependencies before reconfigure."
  return 1
}

_restart_run_model_pipeline() {
  if [ "${RESTART_PRESERVE_CACHE}" = "1" ] || [ "${RESTART_DEPLOY_CHAT}" != "1" ]; then
    return 0
  fi

  if [ "${INFERENCE_ENGINE:-${CFG_DEFAULT_RUNTIME_ENGINE}}" = "${CFG_ENGINE_TRT}" ]; then
    if _restart_needs_trt_engine_build || _restart_needs_awq_pipeline; then
      source "${SCRIPT_DIR}/quantization/trt_quantizer.sh"
    fi
    return 0
  fi

  if _restart_needs_awq_pipeline; then
    source "${SCRIPT_DIR}/quantization/vllm_quantizer.sh"
  fi
}

_restart_push_cached_artifacts() {
  if [ "${HF_AWQ_PUSH:-0}" = "1" ] && [ "${RESTART_PRESERVE_CACHE}" = "1" ]; then
    push_cached_awq_models "${DEPLOY_MODE}"
  fi

  if [ "${RESTART_DEPLOY_CHAT}" != "1" ] ||
    [ "${HF_ENGINE_PUSH:-0}" != "1" ] ||
    [ "${INFERENCE_ENGINE:-${CFG_DEFAULT_RUNTIME_ENGINE}}" != "${CFG_ENGINE_TRT}" ] ||
    [ "${USING_PREBUILT_ENGINE:-0}" = "1" ]; then
    return 0
  fi

  if [ -z "${TRT_ENGINE_DIR:-}" ]; then
    local trt_env_file="${ROOT_DIR}/${CFG_RUNTIME_TRT_ENGINE_ENV_FILE}"
    if [ -f "${trt_env_file}" ]; then
      # shellcheck disable=SC1090
      source "${trt_env_file}"
    fi
  fi
  if [ -n "${TRT_ENGINE_DIR:-}" ] && [ -d "${TRT_ENGINE_DIR}" ]; then
    push_engine_to_hf "${TRT_ENGINE_DIR}" "${CHAT_MODEL:-}"
  else
    log_warn "[restart] --push-engine specified but no TRT engine found to push"
  fi
}

reconfigure_models() {
  _restart_load_previous_config

  local target_deploy
  target_deploy="$(_restart_resolve_deploy_mode)" || exit 1
  export DEPLOY_MODE="${target_deploy}"

  _restart_set_deploy_targets
  _restart_validate_requested_models || exit 1
  _restart_export_requested_models
  _restart_prepare_quantization || exit 1
  _restart_prepare_runtime || exit 1
  _restart_run_model_pipeline
  _restart_push_cached_artifacts
  launch_server_background
}
