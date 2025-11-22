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
  USING_HF_MODELS=0

  if [ -d "${AWQ_CACHE_DIR}" ]; then
    local LOCAL_CHAT_OK=0 LOCAL_TOOL_OK=0
    if [ -f "${CHAT_AWQ_DIR}/awq_config.json" ] || [ -f "${CHAT_AWQ_DIR}/.awq_ok" ]; then LOCAL_CHAT_OK=1; fi
    if [ -f "${TOOL_AWQ_DIR}/awq_config.json" ] || [ -f "${TOOL_AWQ_DIR}/.awq_ok" ]; then LOCAL_TOOL_OK=1; fi
    case "${DEPLOY_MODE}" in
      both) [ "${LOCAL_CHAT_OK}" = "1" ] && [ "${LOCAL_TOOL_OK}" = "1" ] && USING_LOCAL_MODELS=1 ;;
      chat) [ "${LOCAL_CHAT_OK}" = "1" ] && USING_LOCAL_MODELS=1 ;;
      tool) [ "${LOCAL_TOOL_OK}" = "1" ] && USING_LOCAL_MODELS=1 ;;
    esac
  fi

  local HF_CHAT_OK=0 HF_TOOL_OK=0
  if [ -n "${AWQ_CHAT_MODEL:-}" ]; then HF_CHAT_OK=1; fi
  if [ -n "${AWQ_TOOL_MODEL:-}" ]; then HF_TOOL_OK=1; fi
  case "${DEPLOY_MODE}" in
    both) [ "${HF_CHAT_OK}" = "1" ] && [ "${HF_TOOL_OK}" = "1" ] && USING_HF_MODELS=1 ;;
    chat) [ "${HF_CHAT_OK}" = "1" ] && USING_HF_MODELS=1 ;;
    tool) [ "${HF_TOOL_OK}" = "1" ] && USING_HF_MODELS=1 ;;
  esac

  export AWQ_CACHE_DIR CHAT_AWQ_DIR TOOL_AWQ_DIR USING_LOCAL_MODELS USING_HF_MODELS
}


restart_setup_env_for_awq() {
  local DEPLOY_MODE="$1"
  export QUANTIZATION=awq
  export DEPLOY_MODELS="${DEPLOY_MODE}"
  if [ "${USING_LOCAL_MODELS}" = "1" ]; then
    if [ "${DEPLOY_MODE}" = "both" ] || [ "${DEPLOY_MODE}" = "chat" ]; then
      export CHAT_MODEL="${CHAT_AWQ_DIR}" CHAT_QUANTIZATION=awq
      if [ -z "${CHAT_MODEL_NAME:-}" ]; then
        CHAT_MODEL_NAME="$(_awq_read_source_model "${CHAT_AWQ_DIR}")"
      fi
    fi
    if [ "${DEPLOY_MODE}" = "both" ] || [ "${DEPLOY_MODE}" = "tool" ]; then
      export TOOL_MODEL="${TOOL_AWQ_DIR}" TOOL_QUANTIZATION=awq
      if [ -z "${TOOL_MODEL_NAME:-}" ]; then
        TOOL_MODEL_NAME="$(_awq_read_source_model "${TOOL_AWQ_DIR}")"
      fi
    fi
  elif [ "${USING_HF_MODELS}" = "1" ]; then
    if [ "${DEPLOY_MODE}" = "both" ] || [ "${DEPLOY_MODE}" = "chat" ]; then
      export CHAT_MODEL="${AWQ_CHAT_MODEL}" CHAT_QUANTIZATION=awq
      if [ -z "${CHAT_MODEL_NAME:-}" ]; then
        CHAT_MODEL_NAME="${AWQ_CHAT_MODEL}"
      fi
    fi
    if [ "${DEPLOY_MODE}" = "both" ] || [ "${DEPLOY_MODE}" = "tool" ]; then
      export TOOL_MODEL="${AWQ_TOOL_MODEL}" TOOL_QUANTIZATION=awq
      if [ -z "${TOOL_MODEL_NAME:-}" ]; then
        TOOL_MODEL_NAME="${AWQ_TOOL_MODEL}"
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
    log_info "HF_AWQ_PUSH=1 but restart is using Hugging Face AWQ models; uploads will be skipped."
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
    log_info "HF_AWQ_PUSH=1 but restart is using Hugging Face AWQ models; skipping upload."
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


