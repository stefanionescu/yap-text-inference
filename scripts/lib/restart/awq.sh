#!/usr/bin/env bash
# shellcheck disable=SC1091
# =============================================================================
# AWQ Model Detection for Restart
# =============================================================================
# Detects cached AWQ models and wires environment variables for restart.sh
# to reuse existing quantized model artifacts.

RESTART_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${RESTART_LIB_DIR}/../common/awq.sh"

_awq_read_source_model() {
  local dir="$1"
  local meta="${dir}/awq_metadata.json"
  if [ ! -f "${meta}" ]; then
    echo ""
    return
  fi
  local python_root="${ROOT_DIR:-$(cd "${RESTART_LIB_DIR}/../../.." && pwd)}"
  PYTHONPATH="${python_root}${PYTHONPATH:+:${PYTHONPATH}}" \
    python3 -m src.scripts.awq source-model "${meta}" 2>/dev/null || true
}

detect_awq_models() {
  local DEPLOY_MODE="$1"
  AWQ_CACHE_DIR="${ROOT_DIR}/.awq"
  CHAT_AWQ_DIR="${AWQ_CACHE_DIR}/chat_awq"
  USING_LOCAL_MODELS=0
  AWQ_SOURCES_READY=1
  CHAT_AWQ_SOURCE=""
  CHAT_AWQ_SOURCE_KIND=""

  local REQUIRE_CHAT=0
  case "${DEPLOY_MODE}" in
    both) REQUIRE_CHAT=1 ;;
    chat) REQUIRE_CHAT=1 ;;
  esac

  local LOCAL_CHAT_OK=0
  local local_chat_dir=""
  if local_chat_dir="$(awq_resolve_local_chat_cache "${ROOT_DIR}")"; then
    LOCAL_CHAT_OK=1
    CHAT_AWQ_DIR="${local_chat_dir}"
  fi

  local last_chat_model last_chat_quant
  last_chat_model="$(read_last_config_value "CHAT_MODEL" "${ROOT_DIR}")"
  last_chat_quant="$(read_last_config_value "CHAT_QUANTIZATION" "${ROOT_DIR}")"

  if [ "${REQUIRE_CHAT}" = "1" ]; then
    if [ "${LOCAL_CHAT_OK}" = "1" ]; then
      CHAT_AWQ_SOURCE="${CHAT_AWQ_DIR}"
      CHAT_AWQ_SOURCE_KIND="local"
    elif [ "${last_chat_quant}" = "awq" ] && [ -n "${last_chat_model}" ]; then
      CHAT_AWQ_SOURCE="${last_chat_model}"
      CHAT_AWQ_SOURCE_KIND="prequant"
    else
      AWQ_SOURCES_READY=0
    fi
  fi

  if [ "${LOCAL_CHAT_OK}" = "1" ]; then
    USING_LOCAL_MODELS=1
  fi

  export AWQ_CACHE_DIR CHAT_AWQ_DIR USING_LOCAL_MODELS
  export AWQ_SOURCES_READY
  export CHAT_AWQ_SOURCE CHAT_AWQ_SOURCE_KIND
}

setup_env_for_awq() {
  local DEPLOY_MODE="$1"
  export DEPLOY_MODE="${DEPLOY_MODE}"
  if [ "${DEPLOY_MODE}" = "both" ] || [ "${DEPLOY_MODE}" = "chat" ]; then
    local chat_source="${CHAT_AWQ_SOURCE:-${CHAT_AWQ_DIR}}"
    export CHAT_MODEL="${chat_source}" CHAT_QUANTIZATION=awq
    if [ -z "${CHAT_MODEL_NAME:-}" ]; then
      if [ "${CHAT_AWQ_SOURCE_KIND:-local}" = "local" ]; then
        CHAT_MODEL_NAME="$(_awq_read_source_model "${chat_source}")"
      else
        CHAT_MODEL_NAME="${chat_source}"
      fi
    fi
  fi
  export CHAT_MODEL_NAME

  if [ "${DEPLOY_MODE}" = "both" ] || [ "${DEPLOY_MODE}" = "tool" ]; then
    local resolved_tool="${TOOL_MODEL:-}"
    if [ -z "${resolved_tool}" ]; then
      resolved_tool="$(read_last_config_value "TOOL_MODEL" "${ROOT_DIR}")"
    fi
    if [ -n "${resolved_tool}" ]; then
      TOOL_MODEL="${resolved_tool}"
    fi
    export TOOL_MODEL
    if [ -z "${TOOL_MODEL_NAME:-}" ] && [ -n "${TOOL_MODEL:-}" ]; then
      TOOL_MODEL_NAME="${TOOL_MODEL}"
    fi
  fi
  export TOOL_MODEL_NAME
}

validate_awq_push_prereqs() {
  local DEPLOY_MODE="$1"
  if [ "${HF_AWQ_PUSH:-0}" != "1" ]; then
    return
  fi
  # Skip AWQ artifact check for TRT - TRT has its own push logic in push_cached_awq_models
  if [ "${INFERENCE_ENGINE:-vllm}" = "trt" ]; then
    return
  fi
  if [ "${USING_LOCAL_MODELS:-0}" != "1" ]; then
    log_info "[restart] --push-quant specified but no local AWQ artifacts detected; uploads will be skipped."
    return
  fi

  # Note: Main prereqs (HF_TOKEN, repo IDs) are validated early in restart.sh
  # via validate_push_quant_prereqs(). This function just checks for local models.
}

push_cached_awq_models() {
  local DEPLOY_MODE="$1"
  if [ "${HF_AWQ_PUSH:-0}" != "1" ]; then
    return
  fi

  # If using TRT engine, push the TRT artifacts (checkpoint + engine)
  if [ "${INFERENCE_ENGINE:-vllm}" = "trt" ]; then
    local engine_dir="${TRT_ENGINE_DIR:-}"
    if [ -d "${engine_dir}" ]; then
      # Derive checkpoint dir from engine dir name and qformat
      local qformat="${TRT_QUANT_METHOD:-int4_awq}"
      local engine_base
      engine_base="$(basename "${engine_dir}")"
      # engine dir pattern: <model>-trt-<qformat>
      local base="${engine_base%-"${qformat}"}"
      base="${base%-trt}"
      local ckpt_dir="${TRT_CACHE_DIR:-${ROOT_DIR}/.trt_cache}/${base}-${qformat}-ckpt"
      if [ -d "${ckpt_dir}" ]; then
        log_info "[restart] Uploading TRT artifacts to Hugging Face"
        push_to_hf "${ckpt_dir}" "${engine_dir}" "${CHAT_MODEL:-}" "${qformat}"
        return
      else
        log_warn "[restart] ⚠ TRT checkpoint directory not found for push: ${ckpt_dir}"
      fi
    else
      log_warn "[restart] ⚠ TRT engine directory not found for push: ${engine_dir}"
    fi
    # Even if TRT push fails, fall through to AWQ push logic
  fi

  if [ "${USING_LOCAL_MODELS:-0}" != "1" ]; then
    log_info "[restart] --push-quant specified but no local AWQ artifacts detected; skipping upload."
    return
  fi

  log_info "[restart] Uploading cached AWQ artifacts to Hugging Face"
  local pushed=0
  if [ "${DEPLOY_MODE}" = "both" ] || [ "${DEPLOY_MODE}" = "chat" ]; then
    vllm_awq_push_to_hf "${CHAT_AWQ_DIR}"
    pushed=1
  fi

  if [ "${pushed}" != "1" ]; then
    log_info "[restart] No local AWQ artifacts matched deploy mode '${DEPLOY_MODE}'; nothing to upload."
  fi
}
