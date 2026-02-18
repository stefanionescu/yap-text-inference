#!/usr/bin/env bash
# =============================================================================
# Restart Pipeline Stages
# =============================================================================

restart_build_main_args_for_engine_switch() {
  build_forward_flags
  RESTART_MAIN_ARGS=("--${INFERENCE_ENGINE}" "--deploy-mode" "${DEPLOY_MODE}")
  RESTART_MAIN_ARGS+=("${ARGS_FORWARD_FLAGS[@]}")

  if [ -n "${RECONFIG_CHAT_QUANTIZATION:-}" ]; then
    case "${RECONFIG_CHAT_QUANTIZATION}" in
      4bit | 4BIT) RESTART_MAIN_ARGS+=("4bit") ;;
      8bit | 8BIT) RESTART_MAIN_ARGS+=("8bit") ;;
    esac
  fi

  case "${DEPLOY_MODE}" in
    chat)
      RESTART_MAIN_ARGS+=("${RECONFIG_CHAT_MODEL:-${CHAT_MODEL:-}}")
      ;;
    tool)
      RESTART_MAIN_ARGS+=("${RECONFIG_TOOL_MODEL:-${TOOL_MODEL:-}}")
      ;;
    both)
      RESTART_MAIN_ARGS+=("${RECONFIG_CHAT_MODEL:-${CHAT_MODEL:-}}")
      RESTART_MAIN_ARGS+=("${RECONFIG_TOOL_MODEL:-${TOOL_MODEL:-}}")
      ;;
  esac
}

restart_stage_parse_and_validate() {
  if ! parse_args "$@"; then
    usage
  fi

  case "${DEPLOY_MODE}" in
    both | chat | tool) : ;;
    *)
      log_warn "[restart] ⚠ Invalid deploy mode '${DEPLOY_MODE}'"
      usage
      ;;
  esac

  export INSTALL_DEPS DEPLOY_MODE INFERENCE_ENGINE
}

restart_stage_preflight() {
  ensure_cuda_ready_for_engine "restart" || return 1

  # Tool-only does not need engine-specific torch stack.
  if [ "${DEPLOY_MODE}" != "tool" ]; then
    torch_cuda_mismatch_guard "[restart]"
    if [ "${TORCHVISION_CUDA_MISMATCH_DETECTED:-0}" = "1" ] && [ "${INSTALL_DEPS:-0}" != "1" ]; then
      log_info "[restart] torch/torchvision mismatch detected; forcing --install-deps for clean reinstall"
      INSTALL_DEPS=1
      export INSTALL_DEPS
    fi
  fi

  return 0
}

restart_stage_engine_switch() {
  local engine_switch_result=0
  handle_engine_switch "${SCRIPT_DIR}" "${ROOT_DIR}" "${INFERENCE_ENGINE}" "${DEPLOY_MODE}" || engine_switch_result=$?

  if [ "${engine_switch_result}" = "2" ]; then
    log_err "[restart] ✗ Engine switch failed"
    return 1
  fi

  # Engine was switched; delegate to full deployment.
  if [ "${engine_switch_result}" = "0" ]; then
    restart_build_main_args_for_engine_switch
    exec bash "${SCRIPT_DIR}/main.sh" "${RESTART_MAIN_ARGS[@]}"
  fi

  return 0
}

restart_stage_awq_cached_flow() {
  detect_awq_models "${DEPLOY_MODE}"

  if [ "${HF_AWQ_PUSH_REQUESTED:-0}" = "1" ] && [ "${CHAT_AWQ_SOURCE_KIND:-}" = "prequant" ]; then
    if [ "${INFERENCE_ENGINE:-}" != "trt" ]; then
      restart_err_prequant_push_quant "${CHAT_AWQ_SOURCE:-}"
      return 1
    fi
  fi

  if [ "${AWQ_SOURCES_READY:-0}" != "1" ]; then
    restart_err_no_awq_sources "${DEPLOY_MODE}"
    return 1
  fi

  log_section "[restart] Stopping server..."
  FULL_CLEANUP=0 "${SCRIPT_DIR}/stop.sh"

  local venv_dir
  venv_dir="${VENV_DIR:-$(get_venv_dir)}"
  if [ "${INSTALL_DEPS:-0}" != "1" ] && [ ! -d "${venv_dir}" ]; then
    log_err "[restart] ✗ No virtual environment found at ${venv_dir}"
    log_err "[restart] ✗ Run with --install-deps to create it, or run full deployment first"
    return 1
  fi

  setup_env_for_awq "${DEPLOY_MODE}"
  push_quant_apply_policy "${CHAT_QUANTIZATION:-}" "restart"
  validate_push_quant_prereqs "${DEPLOY_MODE}"
  push_engine_apply_policy "${INFERENCE_ENGINE:-trt}" "restart"
  validate_push_engine_prereqs
  validate_awq_push_prereqs "${DEPLOY_MODE}"
  if ! validate_models_early; then
    return 1
  fi

  apply_defaults_and_deps
  push_cached_awq_models "${DEPLOY_MODE}"

  if [ "${INFERENCE_ENGINE:-vllm}" = "trt" ] && [ "${DEPLOY_MODE}" != "tool" ]; then
    if [ -z "${TRT_ENGINE_DIR:-}" ] || [ ! -d "${TRT_ENGINE_DIR:-}" ]; then
      restart_err_missing_trt_engine "${DEPLOY_MODE}"
      return 1
    fi

    # Skip pushing back engines that were downloaded from HF.
    if [ "${HF_ENGINE_PUSH:-0}" = "1" ] && [ "${USING_PREBUILT_ENGINE:-0}" != "1" ]; then
      push_engine_to_hf "${TRT_ENGINE_DIR}" "${CHAT_MODEL:-}"
    fi
  fi

  launch_server_background
  return 0
}

restart_stage_run_mode() {
  if [ "${RESTART_MODEL_MODE}" = "reconfigure" ]; then
    reconfigure_models
    return 0
  fi

  # Generic path may fully handle restart (and stream logs). If it decides not to,
  # execution continues into AWQ cached flow.
  run_basic_restart
  restart_stage_awq_cached_flow
}

restart_main() {
  log_info "[restart] Restarting server..."

  ensure_required_env_vars

  export VENV_DIR="${VENV_DIR:-$(get_venv_dir)}"
  gpu_init_detection "gpu"
  gpu_apply_env_defaults
  stop_existing_warmup_processes "${ROOT_DIR}"

  restart_stage_parse_and_validate "$@"
  restart_stage_preflight || return 1
  restart_stage_engine_switch || return 1

  if [ "${DEPLOY_MODE}" != "tool" ]; then
    log_section "[restart] Engine: ${INFERENCE_ENGINE}"
  fi

  restart_stage_run_mode
}
