#!/usr/bin/env bash

# AWQ model detection and environment wiring for scripts/restart.sh
# Requires: ROOT_DIR

_awq_read_source_model() {
  local dir="$1"
  local meta="${dir}/awq_metadata.json"
  if [ ! -f "${meta}" ]; then
    echo ""
    return
  fi
  python3 - <<'PY' "${meta}" || true
import json, sys
path = sys.argv[1]
try:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    source = (data.get("source_model") or "").strip()
    if source:
        print(source)
except Exception:
    pass
PY
}

restart_detect_awq_models() {
  local DEPLOY_MODE="$1"
  AWQ_CACHE_DIR="${ROOT_DIR}/.awq"
  CHAT_AWQ_DIR="${AWQ_CACHE_DIR}/chat_awq"
  TOOL_AWQ_DIR="${AWQ_CACHE_DIR}/tool_awq"
  USING_LOCAL_MODELS=0
  AWQ_SOURCES_READY=1
  CHAT_AWQ_SOURCE=""
  TOOL_AWQ_SOURCE=""
  CHAT_AWQ_SOURCE_KIND=""
  TOOL_AWQ_SOURCE_KIND=""

  local REQUIRE_CHAT=0 REQUIRE_TOOL=0
  case "${DEPLOY_MODE}" in
    both) REQUIRE_CHAT=1; REQUIRE_TOOL=1 ;;
    chat) REQUIRE_CHAT=1 ;;
    tool) REQUIRE_TOOL=1 ;;
  esac

  local LOCAL_CHAT_OK=0 LOCAL_TOOL_OK=0
  if [ -d "${AWQ_CACHE_DIR}" ]; then
    if [ -f "${CHAT_AWQ_DIR}/.awq_ok" ] || [ -f "${CHAT_AWQ_DIR}/awq_metadata.json" ] || [ -f "${CHAT_AWQ_DIR}/awq_config.json" ]; then LOCAL_CHAT_OK=1; fi
    if [ -f "${TOOL_AWQ_DIR}/.awq_ok" ] || [ -f "${TOOL_AWQ_DIR}/awq_metadata.json" ] || [ -f "${TOOL_AWQ_DIR}/awq_config.json" ]; then LOCAL_TOOL_OK=1; fi
  fi

  local last_chat_model last_tool_model last_quant last_chat_quant last_tool_quant
  last_chat_model="$(runtime_guard_read_last_config_value "CHAT_MODEL" "${ROOT_DIR}")"
  last_tool_model="$(runtime_guard_read_last_config_value "TOOL_MODEL" "${ROOT_DIR}")"
  last_quant="$(runtime_guard_read_last_config_value "QUANTIZATION" "${ROOT_DIR}")"
  last_chat_quant="$(runtime_guard_read_last_config_value "CHAT_QUANTIZATION" "${ROOT_DIR}")"
  last_tool_quant="$(runtime_guard_read_last_config_value "TOOL_QUANTIZATION" "${ROOT_DIR}")"

  local effective_chat_quant effective_tool_quant
  effective_chat_quant="${last_chat_quant:-${last_quant:-}}"
  effective_tool_quant="${last_tool_quant:-${last_quant:-}}"

  if [ "${REQUIRE_CHAT}" = "1" ]; then
    if [ "${LOCAL_CHAT_OK}" = "1" ]; then
      CHAT_AWQ_SOURCE="${CHAT_AWQ_DIR}"
      CHAT_AWQ_SOURCE_KIND="local"
    elif [ "${effective_chat_quant}" = "awq" ] && [ -n "${last_chat_model}" ]; then
      CHAT_AWQ_SOURCE="${last_chat_model}"
      CHAT_AWQ_SOURCE_KIND="prequant"
    fi
  fi

  if [ "${REQUIRE_TOOL}" = "1" ]; then
    if [ "${LOCAL_TOOL_OK}" = "1" ]; then
      TOOL_AWQ_SOURCE="${TOOL_AWQ_DIR}"
      TOOL_AWQ_SOURCE_KIND="local"
    elif [ "${effective_tool_quant}" = "awq" ] && [ -n "${last_tool_model}" ]; then
      TOOL_AWQ_SOURCE="${last_tool_model}"
      TOOL_AWQ_SOURCE_KIND="prequant"
    fi
  fi

  if [ "${REQUIRE_CHAT}" = "1" ] && [ -z "${CHAT_AWQ_SOURCE_KIND}" ]; then
    AWQ_SOURCES_READY=0
  fi
  if [ "${REQUIRE_TOOL}" = "1" ] && [ -z "${TOOL_AWQ_SOURCE_KIND}" ]; then
    AWQ_SOURCES_READY=0
  fi

  case "${DEPLOY_MODE}" in
    both) [ "${LOCAL_CHAT_OK}" = "1" ] && [ "${LOCAL_TOOL_OK}" = "1" ] && USING_LOCAL_MODELS=1 ;;
    chat) [ "${LOCAL_CHAT_OK}" = "1" ] && USING_LOCAL_MODELS=1 ;;
    tool) [ "${LOCAL_TOOL_OK}" = "1" ] && USING_LOCAL_MODELS=1 ;;
  esac

  export AWQ_CACHE_DIR CHAT_AWQ_DIR TOOL_AWQ_DIR USING_LOCAL_MODELS
  export AWQ_SOURCES_READY
  export CHAT_AWQ_SOURCE TOOL_AWQ_SOURCE
  export CHAT_AWQ_SOURCE_KIND TOOL_AWQ_SOURCE_KIND
}

restart_setup_env_for_awq() {
  local DEPLOY_MODE="$1"
  export QUANTIZATION=awq
  export DEPLOY_MODELS="${DEPLOY_MODE}"
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
  if [ "${DEPLOY_MODE}" = "both" ] || [ "${DEPLOY_MODE}" = "tool" ]; then
    local tool_source="${TOOL_AWQ_SOURCE:-${TOOL_AWQ_DIR}}"
    export TOOL_MODEL="${tool_source}" TOOL_QUANTIZATION=awq
    if [ -z "${TOOL_MODEL_NAME:-}" ]; then
      if [ "${TOOL_AWQ_SOURCE_KIND:-local}" = "local" ]; then
        TOOL_MODEL_NAME="$(_awq_read_source_model "${tool_source}")"
      else
        TOOL_MODEL_NAME="${tool_source}"
      fi
    fi
  fi
  export CHAT_MODEL_NAME TOOL_MODEL_NAME
}

restart_validate_awq_push_prereqs() {
  local DEPLOY_MODE="$1"
  if [ "${HF_AWQ_PUSH:-0}" != "1" ]; then
    return
  fi
  if [ "${USING_LOCAL_MODELS:-0}" != "1" ]; then
    log_info "HF_AWQ_PUSH=1 but no local AWQ artifacts detected; uploads will be skipped."
    return
  fi

  if [ -z "${HF_TOKEN:-}" ]; then
    log_error "HF_AWQ_PUSH=1 requires HF_TOKEN (or HUGGINGFACE_HUB_TOKEN) to be set before restart."
    exit 1
  fi

  local NEED_CHAT=0 NEED_TOOL=0
  case "${DEPLOY_MODE}" in
    both) NEED_CHAT=1; NEED_TOOL=1 ;;
    chat) NEED_CHAT=1 ;;
    tool) NEED_TOOL=1 ;;
  esac

  if [ "${NEED_CHAT}" = "1" ]; then
    if [ -z "${HF_AWQ_CHAT_REPO:-}" ] || [[ "${HF_AWQ_CHAT_REPO}" == your-org/* ]]; then
      log_error "HF_AWQ_PUSH=1 requires HF_AWQ_CHAT_REPO to point to your Hugging Face chat repo."
      exit 1
    fi
  fi

  if [ "${NEED_TOOL}" = "1" ]; then
    if [ -z "${HF_AWQ_TOOL_REPO:-}" ] || [[ "${HF_AWQ_TOOL_REPO}" == your-org/* ]]; then
      log_error "HF_AWQ_PUSH=1 requires HF_AWQ_TOOL_REPO to point to your Hugging Face tool repo."
      exit 1
    fi
  fi
}

restart_push_cached_awq_models() {
  local DEPLOY_MODE="$1"
  if [ "${HF_AWQ_PUSH:-0}" != "1" ]; then
    return
  fi
  if [ "${USING_LOCAL_MODELS:-0}" != "1" ]; then
    log_info "HF_AWQ_PUSH=1 but no local AWQ artifacts detected; skipping upload."
    return
  fi

  log_info "Uploading cached AWQ artifacts to Hugging Face (restart)"
  local pushed=0
  if [ "${DEPLOY_MODE}" = "both" ] || [ "${DEPLOY_MODE}" = "chat" ]; then
    push_awq_to_hf "${CHAT_AWQ_DIR}" "${HF_AWQ_CHAT_REPO}" "${HF_AWQ_COMMIT_MSG_CHAT}"
    pushed=1
  fi
  if [ "${DEPLOY_MODE}" = "both" ] || [ "${DEPLOY_MODE}" = "tool" ]; then
    push_awq_to_hf "${TOOL_AWQ_DIR}" "${HF_AWQ_TOOL_REPO}" "${HF_AWQ_COMMIT_MSG_TOOL}"
    pushed=1
  fi

  if [ "${pushed}" != "1" ]; then
    log_info "No local AWQ artifacts matched deploy mode '${DEPLOY_MODE}'; nothing to upload."
  fi
}


