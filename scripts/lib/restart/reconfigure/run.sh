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
  # Clear stale TRT engine path reference
  rm -f "${ROOT_DIR}/${CFG_RUNTIME_TRT_ENGINE_ENV_FILE}" 2>/dev/null || true

  local deploy_mode="${DEPLOY_MODE:-${CFG_DEFAULT_DEPLOY_MODE}}"

  # Model-specific artifacts (always clear on model switch)
  local model_paths=(
    "${ROOT_DIR}/.awq"
    "${ROOT_DIR}/.trt_cache"
    "${ROOT_DIR}/models"
  )

  # Tool-only mode is engine-agnostic: clear both vLLM and TRT-specific caches.
  if [ "${deploy_mode}" = "${CFG_DEPLOY_MODE_TOOL}" ] ||
    [ "${INFERENCE_ENGINE:-${CFG_DEFAULT_RUNTIME_ENGINE}}" != "${CFG_ENGINE_VLLM}" ]; then
    model_paths+=(
      "${ROOT_DIR}/.vllm_cache"
      "${ROOT_DIR}/.flashinfer"
      "${ROOT_DIR}/.xformers"
    )
  fi

  # TRT engine infrastructure (only clear if NOT using TRT)
  # .trtllm-repo contains quantization scripts - preserve if staying on TRT
  if [ "${deploy_mode}" = "${CFG_DEPLOY_MODE_TOOL}" ] ||
    [ "${INFERENCE_ENGINE:-${CFG_DEFAULT_RUNTIME_ENGINE}}" != "${CFG_ENGINE_TRT}" ]; then
    model_paths+=("${ROOT_DIR}/.trtllm-repo")
  fi

  # HuggingFace caches (model downloads)
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

  for path in "${model_paths[@]}" "${hf_paths[@]}"; do
    if [ -n "${path}" ] && [ -e "${path}" ]; then
      rm -rf "${path}" || true
    fi
  done
}

reconfigure_models() {
  _restart_load_previous_config

  local target_deploy
  target_deploy="$(_restart_resolve_deploy_mode)" || exit 1
  export DEPLOY_MODE="${target_deploy}"

  local deploy_chat deploy_tool
  deploy_chat=0
  deploy_tool=0
  case "${DEPLOY_MODE}" in
    "${CFG_DEPLOY_MODE_BOTH}")
      deploy_chat=1
      deploy_tool=1
      ;;
    "${CFG_DEPLOY_MODE_CHAT}") deploy_chat=1 ;;
    "${CFG_DEPLOY_MODE_TOOL}") deploy_tool=1 ;;
  esac

  local chat_model="${RECONFIG_CHAT_MODEL:-${CHAT_MODEL:-}}"
  local tool_model="${RECONFIG_TOOL_MODEL:-${TOOL_MODEL:-}}"
  if [ "${deploy_chat}" = "1" ] && [ -z "${chat_model}" ]; then
    log_err "[restart] ✗ Chat deployment requested but no chat model supplied."
    log_err "[restart] ✗ Pass --chat-model <repo_or_path> or export CHAT_MODEL before running --reset-models."
    exit 1
  fi
  if [ "${deploy_tool}" = "1" ] && [ -z "${tool_model}" ]; then
    log_err "[restart] ✗ Tool deployment requested but no tool model supplied."
    log_err "[restart] ✗ Pass --tool-model <repo_or_path> or export TOOL_MODEL before running --reset-models."
    exit 1
  fi

  # Validate --push-quant is not used with prequantized models
  if ! validate_push_quant_prequant "${chat_model}" "${tool_model}" "${HF_AWQ_PUSH_REQUESTED:-0}" "[restart]"; then
    exit 1
  fi

  if [ "${deploy_chat}" = "1" ]; then
    export CHAT_MODEL="${chat_model}"
    export CHAT_MODEL_NAME="${chat_model}"
  else
    unset CHAT_MODEL CHAT_MODEL_NAME
  fi

  if [ "${deploy_tool}" = "1" ]; then
    export TOOL_MODEL="${tool_model}"
    export TOOL_MODEL_NAME="${tool_model}"
  else
    unset TOOL_MODEL TOOL_MODEL_NAME
  fi

  local chat_quant="${RECONFIG_CHAT_QUANTIZATION:-${CHAT_QUANTIZATION:-}}"
  if [ -n "${chat_quant}" ]; then
    chat_quant="$(_restart_normalize_quantization_flag "${chat_quant}" "${chat_model}")"
    _restart_validate_quantization "${chat_quant}" || exit 1
  fi

  local chat_hint=""
  if [ "${deploy_chat}" = "1" ]; then
    chat_hint="$(get_quantization_hint "${chat_model}")"
  fi

  quant_resolve_settings \
    "${DEPLOY_MODE}" \
    "${chat_model}" \
    "${RECONFIG_CHAT_QUANTIZATION:-}" \
    "${chat_hint}" \
    "${chat_quant}"

  # Honor --push-quant only when using a 4-bit quantization
  push_quant_apply_policy "${CHAT_QUANTIZATION:-}" "restart"
  validate_push_quant_prereqs "${DEPLOY_MODE}"

  # Honor --push-engine for TRT engine uploads
  push_engine_apply_policy "${INFERENCE_ENGINE:-${CFG_DEFAULT_ENGINE}}" "restart"
  validate_push_engine_prereqs

  # Validate selections against allowlists before continuing
  if ! validate_models_early; then
    exit 1
  fi

  local preserve_cache=0
  if _restart_can_preserve_cache "${deploy_chat}" "${deploy_tool}"; then
    preserve_cache=1
  fi

  log_section "[restart] Reconfiguring models..."

  local resolved_venv="${VENV_DIR:-$(get_venv_dir)}"
  FULL_CLEANUP=0 "${SCRIPT_DIR}/stop.sh"

  if [ "${preserve_cache}" != "1" ]; then
    clear_model_artifacts
  fi

  apply_defaults_and_deps

  if [ ! -d "${resolved_venv}" ]; then
    log_err "[restart] ✗ Virtual environment missing at ${resolved_venv}"
    log_err "[restart] ✗ Re-run with --install-deps to rebuild dependencies before reconfigure."
    exit 1
  fi

  # Run quantization/build pipeline (only if we're NOT preserving cache):
  # - vLLM: only needed for AWQ (FP8/INT8 are runtime quantization)
  # - TRT: ALWAYS needed (all quantization modes require compiled engine)
  if [ "${preserve_cache}" != "1" ] && [ "${deploy_chat}" = "1" ]; then
    if [ "${INFERENCE_ENGINE:-${CFG_DEFAULT_RUNTIME_ENGINE}}" = "${CFG_ENGINE_TRT}" ]; then
      if _restart_needs_trt_engine_build || _restart_needs_awq_pipeline; then
        source "${SCRIPT_DIR}/quantization/trt_quantizer.sh"
      fi
    elif _restart_needs_awq_pipeline; then
      source "${SCRIPT_DIR}/quantization/vllm_quantizer.sh"
    fi
  fi

  # Push to HuggingFace if requested (even when preserving cache)
  # The quantizer scripts above handle push for fresh builds; this handles cached artifacts
  if [ "${HF_AWQ_PUSH:-0}" = "1" ] && [ "${preserve_cache}" = "1" ]; then
    push_cached_awq_models "${DEPLOY_MODE}"
  fi

  # Push TRT engine if requested and we didn't go through the quantizer
  # (quantizer handles its own push; this handles cached/prebuilt engines)
  # Skip if engine was downloaded from HuggingFace (no point pushing back what we downloaded)
  if [ "${deploy_chat}" = "1" ] &&
    [ "${HF_ENGINE_PUSH:-0}" = "1" ] &&
    [ "${INFERENCE_ENGINE:-${CFG_DEFAULT_RUNTIME_ENGINE}}" = "${CFG_ENGINE_TRT}" ] &&
    [ "${USING_PREBUILT_ENGINE:-0}" != "1" ]; then
    # Load engine dir from saved env if not already set
    if [ -z "${TRT_ENGINE_DIR:-}" ]; then
      local trt_env_file="${ROOT_DIR}/${CFG_RUNTIME_TRT_ENGINE_ENV_FILE}"
      if [ -f "${trt_env_file}" ]; then
        # shellcheck disable=SC1090
        source "${trt_env_file}"
        # TRT_ENGINE_DIR is exported directly by the env file
      fi
    fi
    if [ -n "${TRT_ENGINE_DIR:-}" ] && [ -d "${TRT_ENGINE_DIR}" ]; then
      push_engine_to_hf "${TRT_ENGINE_DIR}" "${CHAT_MODEL:-}"
    else
      log_warn "[restart] --push-engine specified but no TRT engine found to push"
    fi
  fi

  launch_server_background
}
