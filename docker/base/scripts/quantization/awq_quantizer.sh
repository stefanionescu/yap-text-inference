#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="/app"
source "${SCRIPT_DIR}/../common/utils.sh"

# Only act for AWQ
if [ "${QUANTIZATION:-}" != "awq" ]; then
  return 0 2>/dev/null || exit 0
fi

log_info "Running AWQ quantization process (Docker Base)"

## Respect pre-quantized setups strictly: if either engine is already AWQ,
## do not perform any additional quantization. We "run like that" and skip.
if [ "${CHAT_QUANTIZATION:-}" = "awq" ] || [ "${TOOL_QUANTIZATION:-}" = "awq" ]; then
  log_info "Detected pre-quantized AWQ for at least one model; skipping runtime quantization to honor existing setup"
  return 0 2>/dev/null || exit 0
fi

export HF_HOME="${HF_HOME:-${ROOT_DIR}/.hf}"
export HUGGINGFACE_HUB_CACHE="${HUGGINGFACE_HUB_CACHE:-${HF_HOME}/hub}"
if [ -f "/etc/ssl/certs/ca-certificates.crt" ]; then
  export REQUESTS_CA_BUNDLE="${REQUESTS_CA_BUNDLE:-/etc/ssl/certs/ca-certificates.crt}"
fi

export HF_HUB_DISABLE_TELEMETRY=1
export HF_HUB_ENABLE_HF_TRANSFER=${HF_HUB_ENABLE_HF_TRANSFER:-0}

push_awq_to_hf() {
  local src_dir="$1"; local repo_id="$2"; local commit_msg="$3"
  if [ "${HF_AWQ_PUSH}" != "1" ]; then return; fi
  if [ -z "${repo_id}" ] || [[ "${repo_id}" == your-org/* ]]; then
    log_warn "HF_AWQ_PUSH=1 but repo not configured; skipping upload for ${src_dir}"; return; fi
  if [[ "${repo_id}" == /* ]]; then
    log_warn "HF_AWQ_PUSH=1 but repo id '${repo_id}' looks like a local path; skipping"; return; fi
  if [ -z "${HF_TOKEN:-}" ]; then
    log_warn "HF_AWQ_PUSH=1 but HF_TOKEN missing; skipping upload"; return; fi
  if [ ! -d "${src_dir}" ]; then
    log_warn "HF AWQ push skipped; directory not found: ${src_dir}"; return; fi
  local python_cmd=("/opt/venv/bin/python" "${ROOT_DIR}/src/awq/utils/hf_push.py" --src "${src_dir}" --repo-id "${repo_id}" --branch "${HF_AWQ_BRANCH}" --token "${HF_TOKEN}")
  if [ "${HF_AWQ_PRIVATE}" = "1" ]; then python_cmd+=(--private); fi
  if [ "${HF_AWQ_ALLOW_CREATE}" != "1" ]; then python_cmd+=(--no-create); fi
  if [ -n "${commit_msg}" ]; then python_cmd+=(--commit-message "${commit_msg}"); fi
  log_info "Uploading AWQ weights from ${src_dir} to Hugging Face repo ${repo_id}"
  HF_TOKEN="${HF_TOKEN}" "${python_cmd[@]}"
}

AWQ_DIR="${ROOT_DIR}/models"
CHAT_AWQ_DIR="${AWQ_DIR}/chat_awq"
TOOL_AWQ_DIR="${AWQ_DIR}/tool_awq"
mkdir -p "${AWQ_DIR}"

USE_PREQUANT_AWQ=0
if [ -n "${AWQ_CHAT_MODEL:-}" ] || [ -n "${AWQ_TOOL_MODEL:-}" ]; then
  USE_PREQUANT_AWQ=1
  log_info "Using pre-quantized AWQ models from Hugging Face"
fi

quantize_model() {
  local name="$1"; local src="$2"; local out_dir="$3"; local commit_msg="$4"; local repo_var="$5"
  if [ -d "${out_dir}" ] && { [ -f "${out_dir}/awq_config.json" ] || [ -f "${out_dir}/.awq_ok" ]; }; then
    log_info "Using existing AWQ ${name} at ${out_dir}"
    echo "${out_dir}"
    return 0
  fi
  log_info "Quantizing ${name} model to AWQ: ${src} -> ${out_dir}"
  if cd "${ROOT_DIR}" && \
     "/opt/venv/bin/python" -m src.awq.quantize --model "${src}" --out "${out_dir}"; then
    push_awq_to_hf "${out_dir}" "${repo_var}" "${commit_msg}"
    echo "${out_dir}"
    return 0
  fi
  return 1
}

# If pre-quantized AWQ provided, assign models accordingly
if [ "${USE_PREQUANT_AWQ}" = "1" ]; then
  if [ "${DEPLOY_TOOL}" = "1" ]; then
    if [ -n "${AWQ_TOOL_MODEL:-}" ]; then
      export TOOL_MODEL="${AWQ_TOOL_MODEL}"; export TOOL_QUANTIZATION=awq
    else
      if OUT=$(quantize_model "tool" "${TOOL_MODEL}" "${TOOL_AWQ_DIR}" "${HF_AWQ_COMMIT_MSG_TOOL:-}" "${HF_AWQ_TOOL_REPO:-}"); then
        export TOOL_MODEL="${OUT}"; export TOOL_QUANTIZATION=awq
      else
        log_warn "AWQ quantization failed for tool model; keeping original"
      fi
    fi
  fi
  if [ "${DEPLOY_CHAT}" = "1" ]; then
    if [ -n "${AWQ_CHAT_MODEL:-}" ]; then
      export CHAT_MODEL="${AWQ_CHAT_MODEL}"; export CHAT_QUANTIZATION=awq
    else
      if [[ "${CHAT_MODEL}" == *GPTQ* ]]; then
        log_warn "AWQ selected but GPTQ chat model provided; refusing."; exit 1
      fi
      if OUT=$(quantize_model "chat" "${CHAT_MODEL}" "${CHAT_AWQ_DIR}" "${HF_AWQ_COMMIT_MSG_CHAT:-}" "${HF_AWQ_CHAT_REPO:-}"); then
        export CHAT_MODEL="${OUT}"; export CHAT_QUANTIZATION=awq
      else
        log_warn "AWQ quantization failed for chat model; keeping original"
      fi
    fi
  fi
else
  # Local quantization for selected engines
  if [ "${DEPLOY_TOOL}" = "1" ]; then
    if OUT=$(quantize_model "tool" "${TOOL_MODEL}" "${TOOL_AWQ_DIR}" "${HF_AWQ_COMMIT_MSG_TOOL:-}" "${HF_AWQ_TOOL_REPO:-}"); then
      export TOOL_MODEL="${OUT}"; export TOOL_QUANTIZATION=awq
    else
      log_warn "AWQ quantization failed for tool model; keeping original"
    fi
  fi
  if [ "${DEPLOY_CHAT}" = "1" ]; then
    if [[ "${CHAT_MODEL}" == *GPTQ* ]]; then
      log_warn "AWQ selected but GPTQ chat model provided; refusing."; exit 1
    fi
    if OUT=$(quantize_model "chat" "${CHAT_MODEL}" "${CHAT_AWQ_DIR}" "${HF_AWQ_COMMIT_MSG_CHAT:-}" "${HF_AWQ_CHAT_REPO:-}"); then
      export CHAT_MODEL="${OUT}"; export CHAT_QUANTIZATION=awq
    else
      log_warn "AWQ quantization failed for chat model; keeping original"
    fi
  fi
fi

log_info "AWQ quantization process completed"


