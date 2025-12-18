#!/usr/bin/env bash

# Push AWQ artifacts to Hugging Face repo
# Only runs when --push-quant flag is passed (sets HF_AWQ_PUSH=1)
# Uses unified params: HF_PUSH_REPO_ID, HF_PUSH_PRIVATE

# Usage: push_awq_to_hf <src_dir>
push_awq_to_hf() {
  local src_dir="$1"

  if [ "${HF_AWQ_PUSH:-0}" != "1" ]; then
    return
  fi

  if [ -z "${HF_PUSH_REPO_ID:-}" ]; then
    log_warn "[hf] --push-quant specified but HF_PUSH_REPO_ID not configured; skipping upload"
    return
  fi

  if [ -z "${HF_TOKEN:-}" ]; then
    log_warn "[hf] --push-quant specified but HF_TOKEN not available; skipping upload"
    return
  fi

  if [ ! -d "${src_dir}" ]; then
    log_warn "[hf] AWQ push skipped; directory not found: ${src_dir}"
    return
  fi

  local python_cmd=(
    "${ROOT_DIR}/.venv/bin/python"
    "${ROOT_DIR}/src/engines/vllm/awq/hf/hf_push.py"
    --src "${src_dir}"
    --repo-id "${HF_PUSH_REPO_ID}"
    --branch main
    --token "${HF_TOKEN}"
  )

  # Add --private flag if HF_PUSH_PRIVATE=1 (default)
  if [ "${HF_PUSH_PRIVATE:-1}" = "1" ]; then
    python_cmd+=(--private)
  fi

  log_info "[hf] Uploading AWQ weights from ${src_dir} to Hugging Face repo ${HF_PUSH_REPO_ID}"
  HF_TOKEN="${HF_TOKEN}" "${python_cmd[@]}"
}


