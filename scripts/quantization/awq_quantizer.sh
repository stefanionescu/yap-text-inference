#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
source "${SCRIPT_DIR}/../utils.sh"

log_info "Running AWQ quantization process"

push_awq_to_hf() {
  local src_dir="$1"
  local repo_id="$2"
  local commit_msg="$3"

  if [ "${HF_AWQ_PUSH}" != "1" ]; then
    return
  fi

  if [ -z "${repo_id}" ] || [[ "${repo_id}" == your-org/* ]]; then
    log_warn "HF_AWQ_PUSH=1 but Hugging Face repo not configured; skipping upload for ${src_dir}"
    return
  fi

  if [[ "${repo_id}" == /* ]]; then
    log_warn "HF_AWQ_PUSH=1 but repo id '${repo_id}' looks like a local path; skipping upload"
    return
  fi

  if [ -z "${HF_TOKEN:-}" ]; then
    log_warn "HF_AWQ_PUSH=1 but no Hugging Face token available; skipping upload"
    return
  fi

  if [ ! -d "${src_dir}" ]; then
    log_warn "HF AWQ push skipped; directory not found: ${src_dir}"
    return
  fi

  local python_cmd=("${ROOT_DIR}/.venv/bin/python" "${ROOT_DIR}/src/awq/utils/hf_push.py" --src "${src_dir}" --repo-id "${repo_id}" --branch "${HF_AWQ_BRANCH}" --token "${HF_TOKEN}")
  if [ "${HF_AWQ_PRIVATE}" = "1" ]; then
    python_cmd+=(--private)
  fi
  if [ "${HF_AWQ_ALLOW_CREATE}" != "1" ]; then
    python_cmd+=(--no-create)
  fi
  if [ -n "${commit_msg}" ]; then
    python_cmd+=(--commit-message "${commit_msg}")
  fi

  log_info "Uploading AWQ weights from ${src_dir} to Hugging Face repo ${repo_id}"
  HF_TOKEN="${HF_TOKEN}" "${python_cmd[@]}"
}

# Main quantization logic - only run if QUANTIZATION=awq
if [ "${QUANTIZATION}" = "awq" ]; then
  log_info "Starting AWQ quantization process"
  mkdir -p "${AWQ_CACHE_DIR}"
  
  # Quantize TOOL first (if deployed)
  if [ "${DEPLOY_TOOL}" = "1" ]; then
    TOOL_OUT_DIR="${AWQ_CACHE_DIR}/tool_awq"
    if [ -f "${TOOL_OUT_DIR}/awq_config.json" ] || [ -f "${TOOL_OUT_DIR}/.awq_ok" ]; then
      log_info "Using existing AWQ tool model at ${TOOL_OUT_DIR}"
      export TOOL_MODEL="${TOOL_OUT_DIR}"
      push_awq_to_hf "${TOOL_OUT_DIR}" "${HF_AWQ_TOOL_REPO}" "${HF_AWQ_COMMIT_MSG_TOOL}"
    else
      log_info "Quantizing tool model to AWQ: ${TOOL_MODEL} -> ${TOOL_OUT_DIR}"
      if cd "${ROOT_DIR}" && "${ROOT_DIR}/.venv/bin/python" -m src.awq.quantize --model "${TOOL_MODEL}" --out "${TOOL_OUT_DIR}"; then
        export TOOL_MODEL="${TOOL_OUT_DIR}"
        export TOOL_QUANTIZATION=awq
        push_awq_to_hf "${TOOL_OUT_DIR}" "${HF_AWQ_TOOL_REPO}" "${HF_AWQ_COMMIT_MSG_TOOL}"
      else
        log_warn "AWQ quantization failed for tool model; falling back to auto-detected quant (float)"
        unset TOOL_QUANTIZATION
        if [ "${AWQ_FAIL_HARD:-0}" = "1" ]; then
          log_warn "AWQ_FAIL_HARD=1 set; aborting"
          exit 1
        else
          log_warn "NOTE: Deployment will continue with fallback quantization, not AWQ as requested"
        fi
      fi
    fi
  fi
  
  # Then quantize CHAT (if deployed)
  if [ "${DEPLOY_CHAT}" = "1" ]; then
    CHAT_OUT_DIR="${AWQ_CACHE_DIR}/chat_awq"
    if [[ "${CHAT_MODEL}" == *GPTQ* ]]; then
      log_warn "AWQ selected but GPTQ chat model provided; refusing."
      exit 1
    fi
    if [ ! -f "${CHAT_OUT_DIR}/awq_config.json" ] && [ ! -f "${CHAT_OUT_DIR}/.awq_ok" ]; then
      log_info "Quantizing chat model to AWQ: ${CHAT_MODEL} -> ${CHAT_OUT_DIR}"
      if cd "${ROOT_DIR}" && "${ROOT_DIR}/.venv/bin/python" -m src.awq.quantize --model "${CHAT_MODEL}" --out "${CHAT_OUT_DIR}"; then
        export CHAT_MODEL="${CHAT_OUT_DIR}"
        export CHAT_QUANTIZATION=awq
        push_awq_to_hf "${CHAT_OUT_DIR}" "${HF_AWQ_CHAT_REPO}" "${HF_AWQ_COMMIT_MSG_CHAT}"
      else
        log_warn "AWQ quantization failed for chat model; falling back to auto-detected quant"
        unset CHAT_QUANTIZATION
        if [ "${AWQ_FAIL_HARD:-0}" = "1" ]; then
          log_warn "AWQ_FAIL_HARD=1 set; aborting"
          exit 1
        else
          log_warn "NOTE: Deployment will continue with fallback quantization, not AWQ as requested"
        fi
        # Fallback to auto-detected quant for chat: leave CHAT_MODEL unchanged
      fi
    else
      log_info "Using existing AWQ chat model at ${CHAT_OUT_DIR}"
      export CHAT_MODEL="${CHAT_OUT_DIR}"
      export CHAT_QUANTIZATION=awq
      push_awq_to_hf "${CHAT_OUT_DIR}" "${HF_AWQ_CHAT_REPO}" "${HF_AWQ_COMMIT_MSG_CHAT}"
    fi
  fi
else
  log_info "Quantization mode is '${QUANTIZATION}', skipping AWQ quantization"
fi

log_info "AWQ quantization process completed"
