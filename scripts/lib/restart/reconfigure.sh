#!/usr/bin/env bash

# Helpers for restart.sh reconfigure mode (model/quant switches without reinstalling deps)

RESTART_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${RESTART_LIB_DIR}/../common/model_detect.sh"

_restart_resolve_deploy_mode() {
  local candidate="${RECONFIG_DEPLOY_MODE:-${DEPLOY_MODE:-both}}"
  candidate="${candidate,,}"
  case "${candidate}" in
    both|chat|tool)
      echo "${candidate}"
      ;;
    *)
      log_err "[restart] Invalid deploy mode '${candidate}'. Use --deploy-mode both|chat|tool."
      return 1
      ;;
  esac
}

_restart_is_gptq_model() {
  model_detect_is_gptq_name "$1"
}

_restart_is_awq_model() {
  model_detect_is_awq_name "$1"
}

_restart_autodetect_quantization() {
  local chat_model="$1"
  local chat_enabled="$2"

  if [ "${chat_enabled}" = "1" ]; then
    local chat_hint
    chat_hint="$(model_detect_quantization_hint "${chat_model}")"
    if [ "${chat_hint}" = "awq" ]; then
      echo "awq"
      return
    fi
    if [ "${chat_hint}" = "gptq_marlin" ]; then
      echo "gptq_marlin"
      return
    fi
  fi

  # Return "8bit" placeholder; resolved to fp8 or int8 based on GPU in quantization.sh
  echo "8bit"
}

_restart_normalize_quantization_flag() {
  local value="${1:-}"
  if [ -z "${value}" ]; then
    echo ""
    return
  fi
  local lowered="${value,,}"
  case "${lowered}" in
    4bit)
      echo "awq"
      ;;
    8bit)
      # Return "8bit" placeholder; resolved to fp8 or int8 based on GPU in quantization.sh
      echo "8bit"
      ;;
    *)
      echo "${value}"
      ;;
  esac
}

_restart_validate_quantization() {
  local value="$1"
  case "${value}" in
    8bit|fp8|awq|gptq|gptq_marlin)
      return 0
      ;;
    *)
      log_err "[restart] Invalid quantization '${value}'. Expected 8bit|fp8|gptq|gptq_marlin|awq."
      return 1
      ;;
  esac
}

_restart_needs_awq_pipeline() {
  if [ "${QUANTIZATION:-}" = "awq" ]; then
    return 0
  fi
  if [ "${CHAT_QUANTIZATION:-}" = "awq" ]; then
    return 0
  fi
  return 1
}

# TRT engine always requires a build step (AWQ, FP8, INT8 - all need compiled engines)
_restart_needs_trt_engine_build() {
  if [ "${INFERENCE_ENGINE:-vllm}" = "trt" ]; then
    # Check if engine directory exists and is valid
    local trt_env_file="${ROOT_DIR}/.run/trt_engine_dir.env"
    if [ -f "${trt_env_file}" ]; then
      # shellcheck disable=SC1090
      source "${trt_env_file}"
      if [ -n "${TRTLLM_ENGINE_DIR:-}" ] && [ -d "${TRTLLM_ENGINE_DIR}" ]; then
        # Engine exists - no need to rebuild
        return 1
      fi
    fi
    # No valid engine found - need to build
    return 0
  fi
  return 1
}

_restart_effective_quant() {
  local override="$1"
  local base="$2"
  if [ -n "${override:-}" ]; then
    echo "${override}"
  else
    echo "${base:-}"
  fi
}

_restart_resolve_model_identity() {
  local value="$1"
  if [ -z "${value:-}" ]; then
    echo ""
    return
  fi
  if [[ "${value}" == "${ROOT_DIR}/.awq/"* ]]; then
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
  PREV_QUANTIZATION=""
  PREV_CHAT_QUANTIZATION=""
  PREV_DEPLOY_MODE=""
  PREV_DEPLOY_CHAT=0
  PREV_DEPLOY_TOOL=0

  local last_env="${ROOT_DIR}/.run/last_config.env"
  if [ ! -f "${last_env}" ]; then
    return
  fi

  PREV_CONFIG_FOUND=1

  local cur_chat="${CHAT_MODEL:-}"
  local cur_tool="${TOOL_MODEL:-}"
  local cur_quant="${QUANTIZATION:-}"
  local cur_chat_quant="${CHAT_QUANTIZATION:-}"
  local cur_deploy="${DEPLOY_MODE:-}"
  # shellcheck disable=SC1090
  source "${last_env}" || true

  PREV_CHAT_MODEL="${CHAT_MODEL:-}"
  PREV_TOOL_MODEL="${TOOL_MODEL:-}"
  PREV_QUANTIZATION="${QUANTIZATION:-}"
  PREV_CHAT_QUANTIZATION="${CHAT_QUANTIZATION:-}"
  PREV_DEPLOY_MODE="${DEPLOY_MODE:-}"
  case "${PREV_DEPLOY_MODE}" in
    both) PREV_DEPLOY_CHAT=1; PREV_DEPLOY_TOOL=1 ;;
    chat) PREV_DEPLOY_CHAT=1; PREV_DEPLOY_TOOL=0 ;;
    tool) PREV_DEPLOY_CHAT=0; PREV_DEPLOY_TOOL=1 ;;
    *) PREV_DEPLOY_CHAT=0; PREV_DEPLOY_TOOL=0 ;;
  esac

  CHAT_MODEL="${cur_chat}"
  TOOL_MODEL="${cur_tool}"
  QUANTIZATION="${cur_quant}"
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
    local prev_chat_quant new_chat_quant
    prev_chat_quant="$(_restart_effective_quant "${PREV_CHAT_QUANTIZATION}" "${PREV_QUANTIZATION}")"
    new_chat_quant="$(_restart_effective_quant "${CHAT_QUANTIZATION:-}" "${QUANTIZATION}")"
    if [ "${new_chat_quant}" != "${prev_chat_quant}" ]; then
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

restart_clear_model_artifacts() {
  log_info "[restart] Clearing cached model artifacts for model switch..."
  
  # Model-specific artifacts (always clear on model switch)
  local model_paths=(
    "${ROOT_DIR}/.awq"
    "${ROOT_DIR}/.trt_cache"
    "${ROOT_DIR}/models"
  )
  
  # vLLM engine caches (only clear if NOT using vLLM)
  if [ "${INFERENCE_ENGINE:-vllm}" != "vllm" ]; then
    model_paths+=(
      "${ROOT_DIR}/.vllm_cache"
      "${ROOT_DIR}/.flashinfer"
      "${ROOT_DIR}/.xformers"
    )
  fi
  
  # TRT engine infrastructure (only clear if NOT using TRT)
  # .trtllm-repo contains quantization scripts - preserve if staying on TRT
  if [ "${INFERENCE_ENGINE:-vllm}" != "trt" ]; then
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
      log_info "[restart] Removing ${path}"
      rm -rf "${path}" || true
    fi
  done
}

restart_reconfigure_models() {
  _restart_load_previous_config

  local target_deploy
  target_deploy="$(_restart_resolve_deploy_mode)" || exit 1
  export DEPLOY_MODE="${target_deploy}"

  local deploy_chat deploy_tool
  deploy_chat=0; deploy_tool=0
  case "${DEPLOY_MODE}" in
    both) deploy_chat=1; deploy_tool=1 ;;
    chat) deploy_chat=1 ;;
    tool) deploy_tool=1 ;;
  esac

  local chat_model="${RECONFIG_CHAT_MODEL:-${CHAT_MODEL:-}}"
  local tool_model="${RECONFIG_TOOL_MODEL:-${TOOL_MODEL:-}}"
  if [ "${deploy_chat}" = "1" ] && [ -z "${chat_model}" ]; then
    log_err "[restart] Chat deployment requested but no chat model supplied."
    log_err "[restart] Pass --chat-model <repo_or_path> or export CHAT_MODEL before running --reset-models."
    exit 1
  fi
  if [ "${deploy_tool}" = "1" ] && [ -z "${tool_model}" ]; then
    log_err "[restart] Tool deployment requested but no tool model supplied."
    log_err "[restart] Pass --tool-model <repo_or_path> or export TOOL_MODEL before running --reset-models."
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
    chat_quant="$(_restart_normalize_quantization_flag "${chat_quant}")"
  fi
  local quantization="${QUANTIZATION:-}"
  if [ -n "${quantization}" ]; then
    quantization="$(_restart_normalize_quantization_flag "${quantization}")"
  fi

  if [ "${deploy_chat}" = "1" ] && [ -z "${chat_quant}" ]; then
    chat_quant="$(model_detect_quantization_hint "${chat_model}")"
  fi

  if [ -n "${chat_quant}" ]; then
    if ! _restart_validate_quantization "${chat_quant}"; then
      exit 1
    fi
    quantization="${chat_quant}"
  fi
  if [ -z "${quantization}" ]; then
    quantization="$(_restart_autodetect_quantization "${chat_model}" "${deploy_chat}")"
  fi
  if [ -z "${quantization}" ]; then
    # Default to 8bit placeholder; resolved to fp8 or int8 based on GPU in quantization.sh
    quantization="8bit"
  fi
  if ! _restart_validate_quantization "${quantization}"; then
    exit 1
  fi
  export QUANTIZATION="${quantization}"

  if [ -n "${chat_quant}" ]; then
    export CHAT_QUANTIZATION="${chat_quant}"
  else
    unset CHAT_QUANTIZATION
  fi

  local preserve_cache=0
  if _restart_can_preserve_cache "${deploy_chat}" "${deploy_tool}"; then
    preserve_cache=1
  fi

  log_info "[restart] Restart mode: reconfigure (models reset, deps preserved)"

  log_info "[restart] Stopping server before redeploy (preserving .venv)..."
  NUKE_ALL=0 "${SCRIPT_DIR}/stop.sh"

  if [ "${preserve_cache}" = "1" ]; then
    log_info "[restart] Detected identical model + quantization; preserving all caches and engines."
    log_info "[restart] Skipping quantization/build (everything already in place)."
  else
    restart_clear_model_artifacts
  fi

  restart_apply_defaults_and_deps

  if [ ! -d "${ROOT_DIR}/.venv" ]; then
    log_err "[restart] Virtual environment missing at ${ROOT_DIR}/.venv"
    log_err "[restart] Re-run with --install-deps to rebuild dependencies before reconfigure."
    exit 1
  fi

  # Run quantization/build pipeline (only if we're NOT preserving cache):
  # - vLLM: only needed for AWQ (FP8/INT8 are runtime quantization)
  # - TRT: ALWAYS needed (all quantization modes require compiled engine)
  if [ "${preserve_cache}" != "1" ]; then
    if [ "${INFERENCE_ENGINE:-vllm}" = "trt" ]; then
      if _restart_needs_trt_engine_build || _restart_needs_awq_pipeline; then
        log_info "[restart] Building TRT-LLM engine (required for TRT deployment)..."
        source "${SCRIPT_DIR}/quantization/trt_quantizer.sh"
      else
        log_info "[restart] TRT engine already exists, skipping build"
      fi
    elif _restart_needs_awq_pipeline; then
      source "${SCRIPT_DIR}/quantization/vllm_quantizer.sh"
    fi
  fi

  restart_server_background
}
