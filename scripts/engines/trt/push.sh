#!/usr/bin/env bash
# =============================================================================
# TRT-LLM Hugging Face Push
# =============================================================================
# Push TRT-LLM quantized models to Hugging Face.
#
# Two modes:
# 1. Full push (--push-quant): Push checkpoint + engine to a new/existing repo
#    Only runs when --push-quant flag is passed (sets HF_AWQ_PUSH=1)
# 2. Engine-only push (--push-engine): Push only engine to existing prequant repo
#    Only runs when --push-engine flag is passed (sets HF_ENGINE_PUSH=1)
#
# Uses unified params: HF_PUSH_REPO_ID, HF_PUSH_PRIVATE

# Push quantized model to HuggingFace
# Usage: push_to_hf <checkpoint_dir> [engine_dir] [base_model] [quant_method]
push_to_hf() {
  local checkpoint_dir="${1:-${TRT_CHECKPOINT_DIR:-}}"
  local engine_dir="${2:-${TRT_ENGINE_DIR:-}}"
  local base_model="${3:-${CHAT_MODEL:-}}"
  local quant_method="${4:-${TRT_QUANT_METHOD:-int4_awq}}"
  
  if [ "${HF_AWQ_PUSH:-0}" != "1" ]; then
    log_info "[hf] HF push not enabled (use --push-quant flag to enable)"
    return 0
  fi
  
  if [ -z "${HF_PUSH_REPO_ID:-}" ]; then
    log_warn "[hf] ⚠ --push-quant specified but HF_PUSH_REPO_ID not set; skipping push"
    return 0
  fi
  
  if [ ! -d "${checkpoint_dir}" ]; then
    log_warn "[hf] ⚠ Checkpoint directory not found: ${checkpoint_dir}"
    return 1
  fi
  
  local token="${HF_TOKEN:-}"
  if [ -z "${token}" ]; then
    log_warn "[hf] ⚠ HF_TOKEN not set, skipping push"
    return 1
  fi
  
  log_blank
  log_info "[hf] Pushing quantized model to HuggingFace..."
  
  # Pick a python interpreter (prefer venv, then system)
  local python_exe="${HF_PYTHON:-}"
  if [ -n "${python_exe}" ] && [ ! -x "${python_exe}" ]; then
    log_warn "[hf] ⚠ HF_PYTHON=${python_exe} not executable; falling back"
    python_exe=""
  fi
  if [ -z "${python_exe}" ]; then
    if [ -x "${ROOT_DIR}/.venv/bin/python" ]; then
      python_exe="${ROOT_DIR}/.venv/bin/python"
    elif command -v python3 >/dev/null 2>&1; then
      python_exe="$(command -v python3)"
    elif command -v python >/dev/null 2>&1; then
      python_exe="$(command -v python)"
    else
      log_err "[hf] ✗ No python interpreter found (.venv, python3, python)"
      return 1
    fi
  fi
  
  local python_cmd=(
    "${python_exe}"
    "-W" "ignore::RuntimeWarning"
    "-m" "src.hf.trt.hf_push"
    "push"
    "--checkpoint-dir" "${checkpoint_dir}"
    "--repo-id" "${HF_PUSH_REPO_ID}"
    "--token" "${token}"
    "--quant-method" "${quant_method}"
  )
  
  # Add --private flag if HF_PUSH_PRIVATE=1 (default)
  if [ "${HF_PUSH_PRIVATE:-1}" = "1" ]; then
    python_cmd+=("--private")
  fi
  
  # Add engine dir if it exists
  if [ -n "${engine_dir}" ] && [ -d "${engine_dir}" ]; then
    python_cmd+=("--engine-dir" "${engine_dir}")
  fi
  
  # Add base model if specified
  if [ -n "${base_model}" ]; then
    python_cmd+=("--base-model" "${base_model}")
  fi
  
  if "${python_cmd[@]}"; then
    log_info "[hf] ✓ Pushed to HuggingFace"
    return 0
  else
    log_warn "[hf] ⚠ HuggingFace push failed"
    return 1
  fi
}

# Push only the TRT engine to an existing HuggingFace repo (for prequantized models)
# Usage: push_engine_to_hf <engine_dir> <source_repo_id>
# 
# This is used when:
# - Using a pre-quantized TRT model from HuggingFace
# - Building an engine locally for the current GPU
# - Wanting to add that engine to the original repo for future reuse
push_engine_to_hf() {
  local engine_dir="${1:-${TRT_ENGINE_DIR:-}}"
  local source_repo="${2:-${CHAT_MODEL:-}}"
  
  if [ "${HF_ENGINE_PUSH:-0}" != "1" ]; then
    log_info "[hf] Engine push not enabled (use --push-engine flag to enable)"
    return 0
  fi
  
  if [ -z "${engine_dir}" ] || [ ! -d "${engine_dir}" ]; then
    log_warn "[hf] ⚠ Engine directory not found: ${engine_dir}"
    return 1
  fi
  
  # Validate engine files exist
  if ! ls "${engine_dir}"/rank*.engine >/dev/null 2>&1; then
    log_warn "[hf] ⚠ No rank*.engine files found in ${engine_dir}"
    return 1
  fi
  
  # Determine the target repo - use source repo if it looks like a HF repo ID
  local target_repo="${source_repo}"
  if [ -z "${target_repo}" ]; then
    log_warn "[hf] ⚠ No source repo specified for engine push"
    log_warn "[hf]   Set CHAT_MODEL to the HuggingFace repo ID"
    return 1
  fi
  
  # Validate it looks like a HF repo (owner/name format)
  if ! echo "${target_repo}" | grep -q '/'; then
    log_warn "[hf] ⚠ Source model '${target_repo}' does not look like a HuggingFace repo ID"
    log_warn "[hf]   Expected format: owner/model-name"
    return 1
  fi
  
  local token="${HF_TOKEN:-}"
  if [ -z "${token}" ]; then
    log_warn "[hf] ⚠ HF_TOKEN not set, skipping engine push"
    return 1
  fi
  
  log_blank
  log_info "[hf] Pushing engine to existing HF repo..."
  
  # Pick a python interpreter (prefer venv, then system)
  local python_exe="${HF_PYTHON:-}"
  if [ -n "${python_exe}" ] && [ ! -x "${python_exe}" ]; then
    log_warn "[hf] ⚠ HF_PYTHON=${python_exe} not executable; falling back"
    python_exe=""
  fi
  if [ -z "${python_exe}" ]; then
    if [ -x "${ROOT_DIR}/.venv/bin/python" ]; then
      python_exe="${ROOT_DIR}/.venv/bin/python"
    elif command -v python3 >/dev/null 2>&1; then
      python_exe="$(command -v python3)"
    elif command -v python >/dev/null 2>&1; then
      python_exe="$(command -v python)"
    else
      log_err "[hf] ✗ No python interpreter found (.venv, python3, python)"
      return 1
    fi
  fi
  
  local python_cmd=(
    "${python_exe}"
    "-W" "ignore::RuntimeWarning"
    "-m" "src.hf.trt.hf_push"
    "push-engine"
    "--engine-dir" "${engine_dir}"
    "--repo-id" "${target_repo}"
    "--token" "${token}"
  )
  
  if "${python_cmd[@]}"; then
    log_info "[hf] ✓ Engine pushed to HuggingFace"
    return 0
  else
    log_warn "[hf] ⚠ HuggingFace engine push failed"
    return 1
  fi
}

