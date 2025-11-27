#!/usr/bin/env bash

# Core AWQ operations (selection and quantization helpers)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../common/model_detect.sh"

awq_ensure_cache_dir() {
  mkdir -p "${AWQ_CACHE_DIR}"
}

# Resolve a HF repo to a local path via snapshot_download
# Stores metadata about the source model for restart detection
_awq_resolve_prequant_model() {
  local model_repo="$1"
  local cache_dir="$2"
  local model_type="$3"  # "chat" or "tool"
  local out_dir="${cache_dir}/${model_type}_awq"
  local source_marker="${cache_dir}/.${model_type}_source"

  # If already a local directory with AWQ markers, use it directly
  if [ -d "${model_repo}" ]; then
    if [ -f "${model_repo}/awq_config.json" ] || [ -f "${model_repo}/awq_metadata.json" ]; then
      # Create symlink in cache dir for restart detection
      rm -rf "${out_dir}"
      ln -sfn "$(cd "${model_repo}" && pwd)" "${out_dir}"
      # Store source model info in a separate file (not in symlink target)
      echo "${model_repo}" > "${source_marker}"
      echo "${out_dir}"
      return 0
    fi
  fi

  # Remote HF repo - download and symlink
  local resolved_path
  resolved_path=$("${ROOT_DIR}/.venv/bin/python" - <<PY "${model_repo}" 2>/dev/null || true
import sys
import os
try:
    from huggingface_hub import snapshot_download
    repo_id = sys.argv[1]
    token = os.environ.get("HUGGINGFACE_HUB_TOKEN") or os.environ.get("HF_TOKEN")
    cache_dir = os.environ.get("HF_HOME")
    path = snapshot_download(
        repo_id=repo_id,
        token=token,
        local_files_only=False,
        resume_download=True,
        cache_dir=cache_dir,
    )
    print(path)
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
PY
)

  if [ -z "${resolved_path}" ] || [ ! -d "${resolved_path}" ]; then
    log_warn "Failed to resolve pre-quantized model: ${model_repo}"
    return 1
  fi

  # Verify it has AWQ markers
  if [ ! -f "${resolved_path}/awq_config.json" ] && [ ! -f "${resolved_path}/awq_metadata.json" ]; then
    log_warn "Resolved path ${resolved_path} does not contain AWQ markers"
    return 1
  fi

  # Create symlink in cache dir for restart detection
  rm -rf "${out_dir}"
  ln -sfn "${resolved_path}" "${out_dir}"
  # Store source model info in a separate file (not in symlink target)
  echo "${model_repo}" > "${source_marker}"

  echo "${out_dir}"
  return 0
}

awq_should_use_prequant() {
  local need_chat="${AWQ_TARGET_CHAT:-0}"
  local need_tool="${AWQ_TARGET_TOOL:-0}"
  local use=0 chat_use=0 tool_use=0

  if [ "${need_chat}" = "1" ] && model_detect_is_prequant_awq "${CHAT_MODEL:-}"; then
    chat_use=1
    use=1
  fi
  if [ "${need_tool}" = "1" ] && model_detect_is_prequant_awq "${TOOL_MODEL:-}"; then
    tool_use=1
    use=1
  fi

  export USE_PREQUANT_AWQ=${use}
  export USE_PREQUANT_AWQ_CHAT=${chat_use}
  export USE_PREQUANT_AWQ_TOOL=${tool_use}
}

awq_quantize_tool_if_needed() {
  local out_dir="${AWQ_CACHE_DIR}/tool_awq"
  if [ -f "${out_dir}/.awq_ok" ] || [ -f "${out_dir}/awq_metadata.json" ] || [ -f "${out_dir}/awq_config.json" ]; then
    log_info "Using existing AWQ tool model at ${out_dir}"
    export TOOL_MODEL="${out_dir}"
    export TOOL_QUANTIZATION=awq
    push_awq_to_hf "${out_dir}" "${HF_AWQ_TOOL_REPO}" "${HF_AWQ_COMMIT_MSG_TOOL}"
    return 0
  fi

  log_info "Quantizing tool model to AWQ: ${TOOL_MODEL} -> ${out_dir}"
  if cd "${ROOT_DIR}" && "${ROOT_DIR}/.venv/bin/python" -m src.awq.quantize --model "${TOOL_MODEL}" --out "${out_dir}"; then
    export TOOL_MODEL="${out_dir}"
    export TOOL_QUANTIZATION=awq
    push_awq_to_hf "${out_dir}" "${HF_AWQ_TOOL_REPO}" "${HF_AWQ_COMMIT_MSG_TOOL}"
    return 0
  fi

  log_error "AWQ quantization failed for tool model (${TOOL_MODEL}); aborting deployment."
  return 1
}

awq_quantize_chat_if_needed() {
  local out_dir="${AWQ_CACHE_DIR}/chat_awq"
  if [[ "${CHAT_MODEL}" == *GPTQ* ]]; then
    log_warn "AWQ selected but GPTQ chat model provided; refusing."
    exit 1
  fi

  if [ -f "${out_dir}/.awq_ok" ] || [ -f "${out_dir}/awq_metadata.json" ] || [ -f "${out_dir}/awq_config.json" ]; then
    log_info "Using existing AWQ chat model at ${out_dir}"
    export CHAT_MODEL="${out_dir}"
    export CHAT_QUANTIZATION=awq
    push_awq_to_hf "${out_dir}" "${HF_AWQ_CHAT_REPO}" "${HF_AWQ_COMMIT_MSG_CHAT}"
    return 0
  fi

  log_info "Quantizing chat model to AWQ: ${CHAT_MODEL} -> ${out_dir}"
  if cd "${ROOT_DIR}" && "${ROOT_DIR}/.venv/bin/python" -m src.awq.quantize --model "${CHAT_MODEL}" --out "${out_dir}"; then
    export CHAT_MODEL="${out_dir}"
    export CHAT_QUANTIZATION=awq
    push_awq_to_hf "${out_dir}" "${HF_AWQ_CHAT_REPO}" "${HF_AWQ_COMMIT_MSG_CHAT}"
    return 0
  fi

  log_error "AWQ quantization failed for chat model (${CHAT_MODEL}); aborting deployment."
  return 1
}

awq_handle_tool_prequant_or_quantize() {
  if [ "${USE_PREQUANT_AWQ_TOOL:-0}" = "1" ]; then
    log_info "Detected pre-quantized AWQ tool model: ${TOOL_MODEL}"
    log_info "Resolving and caching for restart compatibility..."
    
    local cached_path
    if cached_path=$(_awq_resolve_prequant_model "${TOOL_MODEL}" "${AWQ_CACHE_DIR}" "tool"); then
      log_info "Pre-quantized tool model cached at: ${cached_path}"
      export TOOL_MODEL="${cached_path}"
      export TOOL_QUANTIZATION=awq
      return 0
    else
      log_warn "Failed to cache pre-quantized tool model; falling back to quantization"
      awq_quantize_tool_if_needed
      return $?
    fi
  fi
  awq_quantize_tool_if_needed
}

awq_handle_chat_prequant_or_quantize() {
  if [ "${USE_PREQUANT_AWQ_CHAT:-0}" = "1" ]; then
    log_info "Detected pre-quantized AWQ chat model: ${CHAT_MODEL}"
    log_info "Resolving and caching for restart compatibility..."
    
    local cached_path
    if cached_path=$(_awq_resolve_prequant_model "${CHAT_MODEL}" "${AWQ_CACHE_DIR}" "chat"); then
      log_info "Pre-quantized chat model cached at: ${cached_path}"
      export CHAT_MODEL="${cached_path}"
      export CHAT_QUANTIZATION=awq
      return 0
    else
      log_warn "Failed to cache pre-quantized chat model; falling back to quantization"
      awq_quantize_chat_if_needed
      return $?
    fi
  fi
  awq_quantize_chat_if_needed
}


