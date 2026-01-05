#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/logs.sh"

cd /app
ROOT_DIR="${ROOT_DIR:-/app}"

# ============================================================================
# Resolve TRT artifacts from HuggingFace if not already present
# ============================================================================
resolve_trt_artifacts() {
  if [ "${DEPLOY_CHAT}" != "1" ]; then
    return 0
  fi
  
  # Check if engine is already baked in
  if [ -f "${TRT_ENGINE_DIR:-/opt/engines/trt-chat}/rank0.engine" ]; then
    return 0
  fi
  
  if [ -z "${TRT_ENGINE_REPO:-}" ]; then
    log_warn "[trt] ⚠ TRT_ENGINE_REPO not set - expecting engine to be mounted at ${TRT_ENGINE_DIR}"
    return 0
  fi
  
  log_info "[trt] Resolving artifacts from ${TRT_ENGINE_REPO}..."
  
  local py_out
  py_out=$(PYTHONPATH="${ROOT_DIR}${PYTHONPATH:+:${PYTHONPATH}}" \
    python /app/download/resolve_artifacts.py 2>&1) || true
  
  local mode
  mode=$(echo "$py_out" | awk -F= '/^MODE=/{print $2; exit}')
  
  case "${mode}" in
    engines)
      TRT_ENGINE_DIR=$(echo "$py_out" | awk -F= '/^ENGINE_DIR=/{print $2; exit}')
      export TRT_ENGINE_DIR
      if [ -f "${TRT_ENGINE_DIR}/rank0.engine" ]; then
        log_info "[trt] Using downloaded engine: ${TRT_ENGINE_DIR}"
      else
        log_err "[trt] ✗ Downloaded engine missing rank0.engine"
        return 1
      fi
      ;;
    checkpoints)
      local checkpoint_dir
      checkpoint_dir=$(echo "$py_out" | awk -F= '/^CHECKPOINT_DIR=/{print $2; exit}')
      if [ -z "${checkpoint_dir}" ] || [ ! -f "${checkpoint_dir}/config.json" ]; then
        log_err "[trt] ✗ Downloaded checkpoint invalid (missing config.json)"
        return 1
      fi
      build_engine_from_checkpoint "${checkpoint_dir}"
      ;;
    none)
      log_warn "[trt] ⚠ No engines or checkpoints found in repo; expecting mounted engine"
      ;;
    error)
      log_err "[trt] ✗ Failed to resolve artifacts"
      echo "$py_out" >&2
      return 1
      ;;
  esac
  
  return 0
}

# ============================================================================
# Build TRT engine from checkpoint
# ============================================================================
build_engine_from_checkpoint() {
  local checkpoint_dir="$1"
  
  : "${TRT_ENGINE_DIR:=/opt/engines/trt-chat}"
  local max_in="${TRT_MAX_INPUT_LEN:-4096}"
  local max_out="${TRT_MAX_OUTPUT_LEN:-512}"
  local max_batch="${TRT_MAX_BATCH_SIZE:-16}"
  
  log_info "[trt] Building engine from checkpoint: ${checkpoint_dir}"
  
  trtllm-build \
    --checkpoint_dir "${checkpoint_dir}" \
    --output_dir "${TRT_ENGINE_DIR}" \
    --gemm_plugin auto \
    --gpt_attention_plugin float16 \
    --context_fmha enable \
    --use_paged_context_fmha enable \
    --kv_cache_type paged \
    --remove_input_padding enable \
    --max_input_len "${max_in}" \
    --max_seq_len "$((max_in + max_out))" \
    --max_batch_size "${max_batch}" \
    --log_level info \
    --workers "$(nproc --all)" || {
      log_err "[trt] ✗ trtllm-build failed from checkpoint"
      return 1
    }
  
  export TRT_ENGINE_DIR
}

# ============================================================================
# Validate engine exists
# ============================================================================
validate_engine() {
  if [ "${DEPLOY_CHAT}" != "1" ]; then
    return 0
  fi
  
  if [ ! -f "${TRT_ENGINE_DIR:-/opt/engines/trt-chat}/rank0.engine" ]; then
    log_err "[trt] ✗ TRT engine not found at ${TRT_ENGINE_DIR}/rank0.engine"
    log_err "[trt]   Either set TRT_ENGINE_REPO or mount an engine directory"
    return 1
  fi
  
  log_success "[trt] ✓ TRT engine validated"
}

# ============================================================================
# Main execution
# ============================================================================

# Resolve artifacts if needed
if ! resolve_trt_artifacts; then
  exit 1
fi

# Validate engine
if ! validate_engine; then
  exit 1
fi

# Resolve uvicorn command
if command -v uvicorn >/dev/null 2>&1; then
  UVICORN_CMD=(uvicorn src.server:app --host 0.0.0.0 --port 8000 --workers 1)
elif command -v python >/dev/null 2>&1 && python -c "import uvicorn" 2>/dev/null; then
  UVICORN_CMD=(python -m uvicorn src.server:app --host 0.0.0.0 --port 8000 --workers 1)
elif command -v python3 >/dev/null 2>&1 && python3 -c "import uvicorn" 2>/dev/null; then
  UVICORN_CMD=(python3 -m uvicorn src.server:app --host 0.0.0.0 --port 8000 --workers 1)
else
  log_err "[trt] ✗ uvicorn not found in container. Ensure dependencies are installed."
  exit 127
fi

log_info "[trt] Starting server..."
"${UVICORN_CMD[@]}" &
SERVER_PID=$!

# Run warmup in background
"${SCRIPT_DIR}/warmup.sh" &

# Wait on server (container stays alive)
wait "${SERVER_PID}"
